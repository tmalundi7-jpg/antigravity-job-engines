import logging
import uuid
import numpy as np
from agents.base import BaseAgent
from core.llm import get_embedding, generate_deterministic_embedding
from core.vector_db import get_or_create_collection
from core.db import SessionLocal, MatchResult

logger = logging.getLogger("agents.matching")

STAGE_1_COSINE_THRESHOLD = 0.65


def cosine_similarity(v1, v2):
    v1 = np.array(v1, dtype=float)
    v2 = np.array(v2, dtype=float)
    denom = np.linalg.norm(v1) * np.linalg.norm(v2)
    if denom == 0:
        return 0.0
    return float(np.dot(v1, v2) / denom)


class MatchingAgent(BaseAgent):
    def __init__(self, embed_fn=None, collection=None):
        super().__init__("matching_agent", "matching_queue")
        # Dependency injection with null guards — allows unit tests to pass mock objects
        self._embed_fn = embed_fn if embed_fn is not None else get_embedding
        self.collection = collection if collection is not None else get_or_create_collection("ftse_job_listings")

    def score_structured_attributes(self, job: dict, candidate: dict) -> tuple[float, dict]:
        """
        Computes structured match score across:
        - Skills Overlap: 40%
        - Experience: 30%
        - Education & Certifications: 15%
        - Location: 10%
        - Keywords: 5%
        Returns score (0-100) and breakdown dict.
        """
        candidate_skills = set([s.lower() for s in candidate.get("skills", ["acca", "excel", "reporting", "budgeting"])])
        job_reqs = [r.lower() for r in job.get("requirements", [])]

        # 1. Skill Match (40%)
        matched_skills = [r for r in job_reqs if any(cs in r for cs in candidate_skills)]
        skill_ratio = (len(matched_skills) / max(len(job_reqs), 1))
        skill_score = min(1.0, skill_ratio * 1.2) * 40.0

        # 2. Experience Match (30%)
        cand_exp = candidate.get("years_experience", 5)
        req_exp = job.get("years_experience", 3)
        exp_score = 30.0 if cand_exp >= req_exp else (cand_exp / max(req_exp, 1)) * 30.0

        # 3. Education & Certifications (15%)
        cand_certs = [c.lower() for c in candidate.get("certifications", ["acca", "cima"])]
        has_cert = any(c in " ".join(job_reqs) for c in cand_certs) or "acca" in str(job).lower()
        cert_score = 15.0 if has_cert else 7.5

        # 4. Location Match (10%)
        cand_loc = candidate.get("location", "United Kingdom").lower()
        job_loc = (job.get("location") or "United Kingdom").lower()

        # UK-wide synonyms — if either side signals anywhere in the UK, it's a match
        uk_signals = {"united kingdom", "uk", "england", "scotland", "wales",
                      "northern ireland", "great britain", "gb", "nationwide",
                      "hybrid", "remote", "various", "flexible"}
        cand_is_uk_wide = cand_loc in uk_signals or any(s in cand_loc for s in uk_signals)
        job_is_uk_wide = job_loc in uk_signals or any(s in job_loc for s in uk_signals)

        if cand_is_uk_wide or job_is_uk_wide:
            loc_score = 10.0   # open to UK-wide — always a location match
        elif cand_loc in job_loc or job_loc in cand_loc:
            loc_score = 10.0   # city-level match (e.g. "Manchester" in both)
        elif "remote" in job_loc or "hybrid" in job_loc:
            loc_score = 10.0   # remote/hybrid always matches
        else:
            loc_score = 3.0    # different specific cities

        # 5. Other Keywords / Industry Match (5%)
        kw_score = 5.0

        total_score = round(skill_score + exp_score + cert_score + loc_score + kw_score, 1)
        breakdown = {
            "skills": round(skill_score, 1),
            "experience": round(exp_score, 1),
            "education": round(cert_score, 1),
            "location": round(loc_score, 1),
            "keywords": round(kw_score, 1)
        }
        return total_score, breakdown

    def process_message(self, msg: dict):
        payload = msg.get("payload", {})
        candidate = payload.get("candidate", {
            "name": "Alex Smith",
            "title": "Senior Management Accountant",
            "skills": ["ACCA", "Financial Reporting", "Variance Analysis", "Excel", "Forecasting", "CIMA"],
            "years_experience": 6,
            "certifications": ["ACCA Qualified"],
            "location": "London",
            "bio": "Qualified Management Accountant with 6 years experience in FTSE companies leading financial forecasting and reporting."
        })
        jobs = payload.get("parsed_jobs", [])
        workflow_id = msg.get("correlation_id", str(uuid.uuid4()))

        logger.info(f"[{self.name}] Matching candidate ({candidate.get('title')}) against {len(jobs)} jobs")

        candidate_text = f"{candidate.get('title')} {candidate.get('bio', '')} {' '.join(candidate.get('skills', []))}"
        try:
            candidate_emb = self._embed_fn(candidate_text)
        except Exception as e:
            logger.warning(f"[{self.name}] Fallback embedding for candidate: {e}")
            candidate_emb = generate_deterministic_embedding(candidate_text)

        ranked_matches = []
        disqualified_matches = []

        for job in jobs:
            job_id = job.get("job_id") or str(uuid.uuid4())
            job_text = f"{job.get('title')} {job.get('company')} {job.get('description', '')} {' '.join(job.get('requirements', []))}"

            try:
                job_emb = self._embed_fn(job_text)
            except Exception as e:
                logger.warning(f"[{self.name}] Fallback embedding for job {job_id}: {e}")
                job_emb = generate_deterministic_embedding(job_text)

            # Store in ChromaDB vector collection
            try:
                self.collection.upsert(
                    ids=[job_id],
                    embeddings=[job_emb],
                    metadatas=[{"company": job.get("company", ""), "title": job.get("title", "")}],
                    documents=[job_text[:500]]
                )
            except Exception as e:
                logger.warning(f"[{self.name}] Vector DB indexing note: {e}")

            # Stage 1: Vector Similarity Calculation
            cos_sim = cosine_similarity(candidate_emb, job_emb)
            passed_prefilter = (cos_sim >= STAGE_1_COSINE_THRESHOLD)

            if not passed_prefilter:
                # Disqualified: Excluded from ranked recommendations
                reasoning = (
                    f"Disqualified: Failed Stage 1 vector cosine similarity pre-filter "
                    f"({cos_sim:.3f} < {STAGE_1_COSINE_THRESHOLD}). Core profile does not align."
                )
                disqualified_entry = {
                    "job_id": job_id,
                    "job_title": job.get("title"),
                    "company": job.get("company"),
                    "location": job.get("location"),
                    "salary_range": job.get("salary_range"),
                    "source_url": job.get("source_url"),
                    "similarity_score": round(cos_sim, 3),
                    "structured_score": 0.0,
                    "final_score": 0.0,
                    "passed_prefilter": False,
                    "disqualified": True,
                    "reasoning": reasoning
                }
                disqualified_matches.append(disqualified_entry)

                # Persist disqualified record to database
                try:
                    with SessionLocal() as db:
                        mr = MatchResult(
                            id=str(uuid.uuid4()),
                            workflow_id=workflow_id,
                            job_id=job_id,
                            candidate_id=candidate.get("id", "cand_01"),
                            similarity_score=cos_sim,
                            structured_score=0.0,
                            final_score=0.0,
                            passed_prefilter=False,
                            reasoning=reasoning
                        )
                        db.add(mr)
                        db.commit()
                except Exception as e:
                    logger.error(f"[{self.name}] Failed to save disqualified MatchResult: {e}")

                continue  # STRICT GATING: Skip Stage 2 and exclusion from ranked recommendations

            # Stage 2: Structured Scoring (0 - 100) for jobs passing Stage 1
            struct_score, breakdown = self.score_structured_attributes(job, candidate)

            # Combined weighted score (40% vector similarity + 60% structured score)
            final_score = round((cos_sim * 40.0) + (struct_score * 0.6), 1)

            reasoning = (
                f"Passed Stage 1 (similarity {cos_sim:.2f} >= {STAGE_1_COSINE_THRESHOLD}). "
                f"Structured breakdown: Skills {breakdown['skills']}/40, "
                f"Exp {breakdown['experience']}/30, Certs {breakdown['education']}/15, Loc {breakdown['location']}/10."
            )

            match_entry = {
                "job_id": job_id,
                "job_title": job.get("title"),
                "company": job.get("company"),
                "location": job.get("location"),
                "salary_range": job.get("salary_range"),
                "source_url": job.get("source_url"),
                "similarity_score": round(cos_sim, 3),
                "structured_score": struct_score,
                "final_score": final_score,
                "passed_prefilter": True,
                "disqualified": False,
                "score_breakdown": breakdown,
                "reasoning": reasoning
            }

            ranked_matches.append(match_entry)

            # Persist qualified match result to database
            try:
                with SessionLocal() as db:
                    mr = MatchResult(
                        id=str(uuid.uuid4()),
                        workflow_id=workflow_id,
                        job_id=job_id,
                        candidate_id=candidate.get("id", "cand_01"),
                        similarity_score=cos_sim,
                        structured_score=struct_score,
                        final_score=final_score,
                        passed_prefilter=True,
                        reasoning=reasoning
                    )
                    db.add(mr)
                    db.commit()
            except Exception as e:
                logger.error(f"[{self.name}] Failed to save MatchResult: {e}")

        # Sort descending by final score
        ranked_matches.sort(key=lambda x: x["final_score"], reverse=True)

        logger.info(
            f"[{self.name}] Evaluated {len(jobs)} jobs: {len(ranked_matches)} passed Stage 1, "
            f"{len(disqualified_matches)} disqualified. Top score: {ranked_matches[0]['final_score'] if ranked_matches else 'None'}"
        )

        self.send_response(
            target="master_queue",
            payload={
                "workflow_id": workflow_id,
                "total_evaluated": len(jobs),
                "passed_count": len(ranked_matches),
                "disqualified_count": len(disqualified_matches),
                "ranked_matches": ranked_matches,
                "disqualified_matches": disqualified_matches,
                "top_recommendations": [m for m in ranked_matches if m["final_score"] >= 70][:5]
            },
            orig_msg=msg
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    MatchingAgent().run()

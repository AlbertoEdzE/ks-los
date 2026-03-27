import os
import sys
import logging

# Ensure project root is in path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from src.core.knowledge_base import KnowledgeBase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Initializing Knowledge Base for Phase 3...")
    
    try:
        kb = KnowledgeBase()
        
        # Clear existing to avoid duplicates/stale data (Clean Slate Protocol)
        logger.info("Clearing existing collection...")
        kb.clear()

        # Ingest Policy
        policy_path = os.path.join(project_root, "doc", "policies", "credit_policy_v1.md")
        if os.path.exists(policy_path):
            kb.ingest_document(policy_path)
            logger.info("Policy ingested successfully.")
        else:
            logger.warning(f"Policy file not found at {policy_path}. Skipping KB policy ingest.")
            return
            
    except Exception as e:
        logger.error(f"Knowledge Base initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

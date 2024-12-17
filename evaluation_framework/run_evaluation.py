import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv

# Local imports
from evaluation import RAGEvaluator
from eval_config import EvalConfig
from system_rag import RAG, create_RAG_eval_app, cleanup_clients
from golden_generation import synthetaze_data


logger = logging.getLogger(__name__)
load_dotenv()

class EvaluationPipeline:
    """Evaluation pipeline orchestrator"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config = EvalConfig.from_file(config_path)
        os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = self.config.deepeval_config["DEEPEVAL_TELEMETRY_OPT_OUT"]
        
    async def run(self) -> Dict[str, Any]:
        """Run complete evaluation pipeline"""
        app = await create_RAG_eval_app()
        
        try:
            logger.info("Starting evaluation pipeline")

            RAG_system = RAG(app)
            evaluator = RAGEvaluator(self.config, app=app)
            eval_data = []

            if self.config.eval_pipeline["use_test_cases"]:
                user_eval_data = evaluator.load_test_cases(self.config.paths["test_cases"])
                eval_data += user_eval_data

            if self.config.eval_pipeline["generate_synthetic_data"]:
                contexts = await RAG_system.get_contexts(top=self.config.synthetic_data["num_retrieved_contexts"])
                context_texts = [[ctx.content] for ctx in contexts if ctx.content]

                goldens = await synthetaze_data(documents=context_texts,
                                                eval_config=self.config,
                                                app_config=app,
                                                gen_from_docs=False)
                goldens_data = evaluator.prepare_goldens(goldens)

                synth_data_path = Path(self.config.paths["synthetic_data_answered"])
                synth_eval_data = await evaluator.prepare_eval_data(goldens_data,
                                                                    RAG_system,
                                                                    synth_data_path)
                eval_data += synth_eval_data

            if len(eval_data) > 0:
                await evaluator._evaluate(eval_data)
                logger.info("Evaluation pipeline completed successfully")
            else:
                raise ValueError("No evaluation data to run")
            
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}")
            raise e
            
        finally:
            await cleanup_clients(app)

async def main():
    pipeline = EvaluationPipeline()
    await asyncio.gather(pipeline.run())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
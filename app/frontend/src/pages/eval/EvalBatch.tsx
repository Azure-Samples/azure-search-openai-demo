import styles from "./Eval.module.css";
import EvalSidebar from "../../components/EvalSidebar/EvalSidebar";
import EvalItem from "../../components/EvalItem/EvalItem";

import { useEffect, useState } from "react";

import * as parameters from "../../data/evaluate_parameters.json";
import * as summary from "../../data/summary.json";
import * as jsonData from "../../data/eval_results.json";
// import * as jsonData from "../../data/eval_results.jsonl";

const str: string = JSON.stringify(jsonData);
const summs: { default: any[] } = JSON.parse(str);

export function Component(): JSX.Element {
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [params, setParams] = useState<any>(parameters);
    const [results, setResults] = useState<any>(summs);
    const [summ, setSummary] = useState<any>(summary);

    // useEffect(() => {
    //     const fetchData = async () => {
    //         try {
    //             console.log("Fetching Data");

    //             setIsLoading(true);
    //             const response = await fetch("../../data/eval_results.jsonl");
    //             const text = await response.text();
    //             const lines = text.split("\n");
    //             const parsedData = lines.map((line: string) => JSON.parse(line));
    //             setResults(parsedData);
    //             console.log(parsedData);
    //         } catch (e) {
    //             console.log(e);
    //         }
    //     };

    //     fetchData();
    // }, []);

    const evaluation_gpt_model = parameters.evaluation_gpt_model;
    const retrieval_mode = parameters.overrides.retrieval_mode;
    const semantic_ranker = parameters.overrides.semantic_ranker;
    const semantic_captions = parameters.overrides.semantic_captions;
    const top = parameters.overrides.top;

    const gpt_groundedness = summ.gpt_groundedness.mean_rating;
    const gpt_relevance = summ.gpt_relevance.mean_rating;
    const gpt_coherence = summ.gpt_coherence.mean_rating;
    const gpt_similarity = summ.gpt_similarity.mean_rating;
    const answer_length = summ.answer_length.mean;
    const answer_has_citation = summ.answer_has_citation.rate;

    console.log(results);

    return (
        <div className={styles.layout}>
            <EvalSidebar />
            <section className={styles.mainContent}>
                <div className={styles.batchScorecard}>
                    <div className={styles.batchScorecardHeader}>
                        <h1>Batch Overview</h1>
                        <button className={styles.evalButton}>Evaluate Batch</button>
                    </div>
                    <div className={styles.batchScorecardContent}>
                        <div className={styles.metricGridElem}>
                            <span>Groundedness</span>
                            {gpt_groundedness}
                        </div>
                        <div className={styles.metricGridElem}>
                            <span>Relevance</span>
                            {gpt_relevance}
                        </div>
                        <div className={styles.metricGridElem}>
                            <span>Coherence</span>
                            {gpt_coherence}
                        </div>
                        <div className={styles.metricGridElem}>
                            <span>Similarity</span>
                            {gpt_similarity}
                        </div>
                        <div className={styles.metricGridElem}>
                            <span>Answer Length</span>
                            {answer_length}
                        </div>
                        <div className={styles.metricGridElem}>
                            <span>Citation Rate</span>
                            {answer_has_citation}
                        </div>
                    </div>
                </div>
                <section>
                    {isLoading ? (
                        <p>Loading...</p>
                    ) : (
                        <>
                            {results.default.map((evalItem: any) => (
                                <EvalItem
                                    key={evalItem.id}
                                    id={evalItem.id}
                                    feedback={evalItem.feedback}
                                    question={evalItem.question}
                                    answer={evalItem.answer}
                                    relevance={evalItem.gpt_relevance}
                                    coherence={evalItem.gpt_coherence}
                                    similarity={evalItem.gpt_similarity}
                                    groundedness={evalItem.gpt_groundedness}
                                />
                            ))}
                        </>
                    )}
                </section>
            </section>
        </div>
    );
}

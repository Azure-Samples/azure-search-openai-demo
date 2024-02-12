import styles from "./BatchExperiment.module.css";

interface Props {
    experimentName: string;
    summ: any;
}
const BatchScorecard = ({ experimentName, summ }: Props) => {
    const gpt_groundedness = summ.gpt_groundedness.mean_rating;
    const gpt_relevance = summ.gpt_relevance.mean_rating;
    const gpt_coherence = summ.gpt_coherence.mean_rating;
    const gpt_similarity = summ.gpt_similarity.mean_rating;
    const answer_length = summ.answer_length.mean;
    const answer_has_citation = summ.answer_has_citation.rate;

    return (
        <div className={styles.batchScorecard}>
            <div className={styles.batchScorecardHeader}>
                <h1>{experimentName}</h1>
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
    );
};
export default BatchScorecard;

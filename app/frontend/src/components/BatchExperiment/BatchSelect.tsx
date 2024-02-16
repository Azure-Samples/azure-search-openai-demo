import { useQuery } from "react-query";

import styles from "./BatchExperiment.module.css";
import { v4 as uuidv4 } from "uuid";

import { getExperimentListApi } from "../../api";

interface Props {
    onBatchClicked: (id: string) => void;
}

const BatchSelect = ({ onBatchClicked }: Props) => {
    const { data, isLoading, error, isError } = useQuery({
        queryKey: ["getExperimentList"],
        queryFn: () => getExperimentListApi(undefined)
    });

    return (
        <div className={styles.batchSelect}>
            <button className={styles.batchEvalButton}>Evaluate New Batch</button>
            {isLoading ? (
                <h1>Loading Available Experiments...</h1>
            ) : (
                <div className={styles.experimentSelect}>
                    {data?.experiment_names.map((batch: string) => (
                        <button key={uuidv4()} className={styles.experiment} onClick={() => onBatchClicked(batch)}>
                            {batch}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
};
export default BatchSelect;

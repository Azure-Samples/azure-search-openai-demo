import { divProperties } from "@fluentui/react";
import { useState, useEffect } from "react";

import styles from "./BatchExperiment.module.css";

interface Props {
    onBatchClicked: (id: string) => void;
}

const BatchSelect = ({ onBatchClicked }: Props) => {
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [data, setData] = useState<any>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setIsLoading(true);
                console.log("Fetching Data");
                const response = await fetch("/experiment_list");
                const jsonData = await response.json();
                setData(jsonData);
                console.log(data);
                setIsLoading(false);
            } catch (e) {
                console.log(e);
            }
        };

        fetchData();
    }, []);

    console.log(data);

    return (
        <div className={styles.batchSelect}>
            <button className={styles.batchEvalButton}>Evaluate New Batch</button>
            {data ? (
                <div className={styles.experimentSelect}>
                    {data.experiment_names.map((batch: string) => (
                        <button className={styles.experiment} onClick={() => onBatchClicked(batch)}>
                            {batch}
                        </button>
                    ))}
                </div>
            ) : (
                <h1>Loading Available Experiments...</h1>
            )}
        </div>
    );
};
export default BatchSelect;

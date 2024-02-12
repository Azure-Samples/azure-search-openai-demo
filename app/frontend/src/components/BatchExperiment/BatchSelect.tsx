import { divProperties } from "@fluentui/react";
import { useState, useEffect } from "react";

import styles from "./BatchExperiment.module.css";
import axios from "axios";
import { v4 as uuidv4 } from "uuid";

interface Props {
    onBatchClicked: (id: string) => void;
}

const BatchSelect = ({ onBatchClicked }: Props) => {
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [data, setData] = useState<any>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setIsLoading(true);
                const response = await axios("/experiment_list");
                const jsonData = await response.data;
                setData(jsonData);
                setIsLoading(false);
            } catch (error) {
                console.log(error);
            }
        };

        fetchData();
    }, []);

    return (
        <div className={styles.batchSelect}>
            <button className={styles.batchEvalButton}>Evaluate New Batch</button>
            {isLoading ? (
                <h1>Loading Available Experiments...</h1>
            ) : (
                <div className={styles.experimentSelect}>
                    {data.experiment_names.map((batch: string) => (
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

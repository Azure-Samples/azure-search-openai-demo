import styles from "./Eval.module.css";
import EvalSidebar from "../../components/EvalSidebar/EvalSidebar";
import EvalItem from "../../components/EvalItem/EvalItem";

import { useEffect, useState } from "react";

import BatchExperiment from "../../components/BatchExperiment/BatchExperiment";
import BatchSelect from "../../components/BatchExperiment/BatchSelect";

import axios from "axios";

export function Component(): JSX.Element {
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [activeBatch, setActiveBatch] = useState<any>(null);
    const [data, setData] = useState<any>(null);

    const onBatchClicked = async (id: string) => {
        try {
            setIsLoading(true);
            setActiveBatch(id);
            console.log("Fetching Data for Batch: " + id);
            const response = await axios("/experiment?name=" + id);
            const jsonData = await response.data;
            setData(jsonData);
            setIsLoading(false);
        } catch (e) {
            console.log(e);
        }
    };

    const removeActiveBatch = () => {
        setActiveBatch(null);
        setData(null);
    };

    return (
        <div className={styles.layout}>
            <EvalSidebar />
            <section className={styles.mainContent}>
                {isLoading ? (
                    <h1>Loading Experiment Data...</h1>
                ) : activeBatch ? (
                    <BatchExperiment jsonData={data} onRemove={removeActiveBatch} />
                ) : (
                    <BatchSelect onBatchClicked={onBatchClicked} />
                )}
            </section>
        </div>
    );
}

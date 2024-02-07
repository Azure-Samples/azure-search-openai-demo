import styles from "./Eval.module.css";
import EvalSidebar from "../../components/EvalSidebar/EvalSidebar";
import EvalItem from "../../components/EvalItem/EvalItem";

import { useEffect, useState } from "react";

import BatchExperiment from "../../components/BatchExperiment/BatchExperiment";
import BatchSelect from "../../components/BatchExperiment/BatchSelect";

export function Component(): JSX.Element {
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [activeBatch, setActiveBatch] = useState<any>(null);
    const [data, setData] = useState<any>(null);

    const onBatchClicked = async (id: string) => {
        setIsLoading(true);
        setActiveBatch(id);
        console.log("Fetching Data for Batch: " + id);
        const response = await fetch("/experiment?name=" + id);
        const jsonData = await response.json();
        console.log(jsonData);
        setData(jsonData);
        setIsLoading(false);
    };

    return (
        <div className={styles.layout}>
            <EvalSidebar />
            <section className={styles.mainContent}>
                {data ? (
                    <BatchExperiment jsonData={data} />
                ) : activeBatch ? (
                    <h1>Loading Experiment Data...</h1>
                ) : (
                    <BatchSelect onBatchClicked={onBatchClicked} />
                )}
            </section>
        </div>
    );
}

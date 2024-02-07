import styles from "./Eval.module.css";
import EvalSidebar from "../../components/EvalSidebar/EvalSidebar";
import EvalItem from "../../components/EvalItem/EvalItem";

import { useEffect, useState } from "react";

import BatchExperiment from "../../components/BatchExperiment/BatchExperiment";
import BatchSelect from "../../components/BatchExperiment/BatchSelect";

export function Component(): JSX.Element {
    // const [isLoading, setIsLoading] = useState<boolean>(false);
    // const [params, setParams] = useState<any>(parameters);
    // const [results, setResults] = useState<any>(summs);
    // const [summ, setSummary] = useState<any>(summary);

    const [activeBatch, setActiveBatch] = useState<any>(null);
    const [data, setData] = useState<any>({});

    const onBatchClicked = (id: number) => {};

    return (
        <div className={styles.layout}>
            <EvalSidebar />
            <section className={styles.mainContent}>
                {activeBatch ? <BatchExperiment jsonData={data} /> : <BatchSelect onBatchClicked={onBatchClicked} />}
            </section>
        </div>
    );
}

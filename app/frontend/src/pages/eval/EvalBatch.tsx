import styles from "./Eval.module.css";

import { useState } from "react";

import EvalSidebar from "../../components/EvalSidebar/EvalSidebar";
import BatchExperiment from "../../components/BatchExperiment/BatchExperiment";
import BatchSelect from "../../components/BatchExperiment/BatchSelect";

export function Component(): JSX.Element {
    const [activeBatch, setActiveBatch] = useState<string | null>(null);

    const onBatchClicked = async (id: string) => {
        setActiveBatch(id);
    };

    const removeActiveBatch = () => {
        setActiveBatch(null);
    };

    return (
        <div className={styles.layout}>
            <EvalSidebar />
            <section className={styles.mainContent}>
                {activeBatch ? <BatchExperiment id={activeBatch} onRemove={removeActiveBatch} /> : <BatchSelect onBatchClicked={onBatchClicked} />}
            </section>
        </div>
    );
}

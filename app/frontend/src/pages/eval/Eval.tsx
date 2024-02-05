import styles from "./Eval.module.css";

import { NavLink } from "react-router-dom";

export function Component(): JSX.Element {
    return (
        <div className={styles.evalTitleContainer}>
            <h1 className={styles.evalTitle}>Evaluate your results</h1>
            <div className={styles.buttonContainer}>
                <NavLink to="/eval_cases" className={styles.evalButton}>
                    Sample Evaluation
                </NavLink>
                <NavLink to="/eval_batch" className={styles.evalButton}>
                    Batch Evaluation
                </NavLink>
            </div>
        </div>
    );
}

import styles from "./Eval.module.css";
import EvalSidebar from "../../components/EvalSidebar/EvalSidebar";

export function Component(): JSX.Element {
    return (
        <div className={styles.layout}>
            <EvalSidebar />
            <section className={styles.mainContent}>
                <div className={styles.batchTitleContainer}>
                    <h1>This Page is Under Construction</h1>
                </div>
            </section>
        </div>
    );
}

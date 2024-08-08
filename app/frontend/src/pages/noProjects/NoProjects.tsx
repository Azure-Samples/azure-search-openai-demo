import styles from "./NoProjects.module.css";

export function Component(): JSX.Element {
    return (
        <div className={styles.container}>
            <h1>No Projects</h1>
            <p>You are not part of any projects. If you believe this is a mistake, contact an administrator.</p>
        </div>
    );
}

Component.displayName = "NoProjects";

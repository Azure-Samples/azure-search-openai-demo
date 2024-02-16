import { useState } from "react";

import styles from "./Summarize.module.css";
import SummarizeSelect from "../../components/Summarize/SummarizeSelect";
import SummarizeDocument from "../../components/Summarize/SummarizeDocument";

export function Component(): JSX.Element {
    const [document, setDocument] = useState<string>("");

    const onDocumentClicked = (document: string) => {
        setDocument(document);
    };

    const removeActiveDocument = () => {
        setDocument("");
    };

    return (
        <div className={styles.layout}>
            <section className={styles.mainContent}>
                {document ? <SummarizeDocument id={document} onRemove={removeActiveDocument} /> : <SummarizeSelect onDocumentClicked={onDocumentClicked} />}
            </section>
        </div>
    );
}

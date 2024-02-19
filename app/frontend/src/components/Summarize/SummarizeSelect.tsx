import { useState } from "react";
import { useQuery } from "react-query";
import { v4 as uuidv4 } from "uuid";

import styles from "./Summarize.module.css";
import { getDocsApi } from "../../api";

interface Props {
    onDocumentClicked: (id: string) => void;
}
const SummarizeSelect = ({ onDocumentClicked }: Props) => {
    const { data, isLoading, error, isError } = useQuery({
        queryKey: ["getDocumentsList"],
        queryFn: () => getDocsApi(undefined)
    });

    return (
        <div className={styles.documentsSelect}>
            {isLoading ? (
                <h1>Loading Available Documents...</h1>
            ) : (
                <div className={styles.documentSelect}>
                    {data?.documents.map((document: string) => (
                        <button key={uuidv4()} className={styles.document} onClick={() => onDocumentClicked(document)}>
                            {document}
                        </button>
                    ))}
                </div>
            )}
            <button className={styles.docUploadButton}>Upload a new document</button>
        </div>
    );
};

export default SummarizeSelect;

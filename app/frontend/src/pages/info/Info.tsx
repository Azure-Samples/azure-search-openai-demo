import { useState, FormEvent, ChangeEvent } from "react";
import { DefaultButton, Dropdown, IDropdownOption } from "@fluentui/react";
import styles from "./Info.module.css";
import { Answer, AnswerError, AnswerLoading } from "../../components/Answer";
export function Component(): JSX.Element {
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [filePreview, setFilePreview] = useState<string | null>(null);
    const [responseData, setResponseData] = useState<any>(null);
    const [statusCode, setStatusCode] = useState<number | null>(null);
    const [selectedParser, setSelectedParser] = useState<string>("invoice");
    const [loading, setLoading] = useState<boolean>(false);
    const [showResponse, setShowResponse] = useState<boolean>(false);
    const [showPreview, setShowPreview] = useState<boolean>(false);

    const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
        if (event.target.files && event.target.files.length > 0) {
            const file = event.target.files[0];
            setSelectedFile(file);
            setFilePreview(URL.createObjectURL(file));
            setShowPreview(true); // Show file preview once file is selected
        }
    };

    const handleDropdownChange = (event: FormEvent<HTMLDivElement>, option?: IDropdownOption): void => {
        if (option) {
            setSelectedParser(option.data);
        }
    };

    const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();

        if (!selectedFile) {
            alert("Please select a file first!");
            return;
        }

        setLoading(true);

        const formData = new FormData();
        formData.append("file", selectedFile);
        formData.append("parser", selectedParser);

        try {
            const response = await fetch("https://langflow-inference.azurewebsites.net/api/parser", {
                method: "POST",
                body: formData,
                redirect: "follow"
            });

            const text = await response.text();
            const parsedResponse = JSON.parse(text);
            const data = JSON.parse(parsedResponse[0]);
            setResponseData(data);
            setStatusCode(response.status);
            setShowResponse(true); // Show response after successful fetch
        } catch (error) {
            console.error("Error:", error);
            setResponseData("An error occurred");
            setStatusCode(null);
        } finally {
            setLoading(false);
        }
    };

    const renderFilePreview = () => {
        if (!filePreview) return null;
        if (selectedFile?.type.startsWith("image/")) {
            return <img src={filePreview} alt="File Preview" className={styles.filePreview} />;
        } else if (selectedFile?.type === "application/pdf") {
            return <embed src={filePreview} type="application/pdf" width="100%" height="600px" />;
        } else {
            return <p>File preview not available for this file type.</p>;
        }
    };

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <h1 className={styles.title}>Information Extraction</h1>
            </div>
            <div className={styles.header}>
                <div className={styles.uploadSection}>
                    <Dropdown
                        className={styles.dropdown}
                        placeholder="Select an option"
                        options={[
                            { key: "invoices", text: "Invoices", data: "invoice" },
                            { key: "sales order", text: "Sales orders", data: "sales order" },
                            { key: "other", text: "General document analysis", data: "other" }
                        ]}
                        onChange={handleDropdownChange}
                        required
                    />
                    <form onSubmit={handleSubmit} className={styles.uploadForm}>
                        <input type="file" onChange={handleFileChange} className={styles.fileInput} />
                        <DefaultButton text="Extract Information" type="submit" className={styles.uploadButton} />
                    </form>
                </div>
            </div>
            <div className={styles.row}>
                <div className={styles.column}>
                    <div className={styles.uploadSection1} style={{ display: showPreview ? "block" : "none" }}>
                        {loading ? (
                            <div className={styles.loader}>
                                <AnswerLoading />
                            </div>
                        ) : (
                            showResponse &&
                            responseData && (
                                <div className={styles.response}>
                                    <h2>Extracted Information:</h2>
                                    <div className={styles.jsonContainer}>
                                        <pre>{JSON.stringify(responseData, null, 2)}</pre>
                                    </div>
                                </div>
                            )
                        )}
                    </div>
                </div>
                <div className={styles.column}>
                    <div className={styles.filePreviewContainer} style={{ display: showPreview ? "block" : "none" }}>
                        {filePreview && <>{renderFilePreview()}</>}
                    </div>
                </div>
            </div>
        </div>
    );
}

Component.displayName = "Ask";

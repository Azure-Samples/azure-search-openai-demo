import { useState, FormEvent, ChangeEvent } from "react";
import { DefaultButton, Dropdown, IDropdownOption } from "@fluentui/react";
import styles from "./Translation.module.css";
import { TranslationLoading } from "../../components/Answer";

export function Component(): JSX.Element {
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [filePreview, setFilePreview] = useState<string | null>(null);
    const [responseData, setResponseData] = useState<string | null>(null);
    const [statusCode, setStatusCode] = useState<number | null>(null);
    const [selectedLanguage, setSelectedLanguage] = useState<string>("es");
    const [loading, setLoading] = useState<boolean>(false);
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
            setSelectedLanguage(option.data);
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
        formData.append("document", selectedFile);
        formData.append("target_language", selectedLanguage);

        try {
            const response = await fetch("https://documents-translation.azurewebsites.net/api/parser", {
                method: "POST",
                body: formData
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                setResponseData(url);
                setStatusCode(response.status);
            } else {
                setResponseData("Failed to translate the document.");
                setStatusCode(response.status);
            }
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
        return <embed src={filePreview} type="application/pdf" width="100%" height="600px" />;
    };

    const renderResponse = () => {
        if (loading) {
            return (
                <div className={styles.loader}>
                    <TranslationLoading />
                </div>
            );
        }

        if (responseData && statusCode === 200) {
            return <embed src={responseData} type="application/pdf" width="100%" height="600px" />;
        } else if (responseData) {
            return <p>{responseData}</p>;
        }

        return null;
    };

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <h1 className={styles.title}>Translation</h1>
            </div>
            <div>
                <form onSubmit={handleSubmit} className={styles.uploadSection}>
                    <input type="file" onChange={handleFileChange} className={styles.fileInput} />
                    <Dropdown
                        className={styles.dropdown}
                        placeholder="Select a Language"
                        options={[{ key: "es", text: "Spanish", data: "es" }]}
                        onChange={handleDropdownChange}
                        required
                    />
                    <DefaultButton text="Translate" type="submit" className={styles.uploadButton} />
                </form>
            </div>
            <div className={styles.row}>
                <div className={styles.column}>{renderFilePreview()}</div>
                <div className={styles.column}>{renderResponse()}</div>
            </div>
        </div>
    );
}

Component.displayName = "TranslationComponent";

import React, { useState } from "react";
import { uploadApi, UploadFileRequest, UploadFileResponse } from "../../api";
import styles from "./FileUploader.module.css";
import { PrimaryButton } from "@fluentui/react";

const FileUploader = () => {
    const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);
    const [uploadStatus, setUploadStatus] = useState<UploadFileResponse[]>([]);
    const handleFileSelection = (event: React.ChangeEvent<HTMLInputElement>) => {
        const formData = new FormData();
        try {
            if (event.target.files) {
                for (let i = 0; i < event.target.files.length; i++) {
                    formData.append("file", event.target.files[i]);
                }
                setSelectedFiles(event.target.files);
                setUploadStatus([]);
            }
        } catch (error) {
            console.log(error);
        }
    };
    const handleUpload = async () => {
        if (!selectedFiles) {
            console.log("No files selected");
            return;
        }
        const formData = new FormData();
        for (let i = 0; i < selectedFiles.length; i++) {
            formData.append("file", selectedFiles[i]);
        }
        try {
            const request: UploadFileRequest = { formData };
            const response = await uploadApi(request);
            const data: UploadFileResponse = await response;
            setUploadStatus(prevStatus => [...prevStatus, data]);
            setSelectedFiles(null); // reset the stat to previous after upload complete
        } catch (error: unknown) {
            if (error instanceof Error) {
                const e: Error = error;
                setUploadStatus(prevStatus => [...prevStatus, { success: false, message: e.message }]);
            }
            setSelectedFiles(null);
        }
    };
    let statusMessage: string | null = null;
    if (uploadStatus.length > 0) {
        const successCount = uploadStatus.filter(status => status.success).length;
        if (successCount === uploadStatus.length) {
            statusMessage = "Upload successful!";
        } else {
            statusMessage = `${successCount} of ${uploadStatus.length} files uploaded successfully\n ${uploadStatus
                .filter(status => !status.success)
                .map(status => status.message)
                .join(", ")}`;
        }
    }
    return (
        <div className={styles.uploadContainer}>
            <div className={styles.uploadTopSection}>
                <h1 className={styles.uploadTitle}>Index your data</h1>
                <div className={styles.fileInputContainer}>
                    <label htmlFor="file-upload" className={styles.uploadButton}>
                        {selectedFiles ? `Upload ${selectedFiles.length} files` : "Choose File to upload"}
                        <input id="file-upload" type="file" onChange={handleFileSelection} multiple className={styles.uploadInput} />
                    </label>
                </div>
            </div>
            <PrimaryButton className={styles.uploadButton} onClick={handleUpload} text="Upload" />
            {statusMessage && <div className={uploadStatus.every(status => status.success) ? styles.successMessage : styles.errorMessage}>{statusMessage}</div>}
        </div>
    );
};
export default FileUploader;

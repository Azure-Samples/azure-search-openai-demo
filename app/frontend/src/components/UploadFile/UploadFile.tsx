import React, { useState, ChangeEvent } from "react";
import { Callout, Label, Text } from "@fluentui/react";
import { Button } from "@fluentui/react-components";
import { Add24Regular, Delete24Regular } from "@fluentui/react-icons";
import { useMsal } from "@azure/msal-react";

import { SimpleAPIResponse, uploadFileApi, deleteUploadedFileApi, listUploadedFilesApi } from "../../api";
import { useLogin, getToken } from "../../authConfig";
import styles from "./UploadFile.module.css";

interface Props {
    className?: string;
    disabled?: boolean;
}

export const UploadFile: React.FC<Props> = ({ className, disabled }: Props) => {
    // State variables to manage the component behavior
    const [isCalloutVisible, setIsCalloutVisible] = useState<boolean>(false);
    const [isUploading, setIsUploading] = useState<boolean>(false);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [uploadedFile, setUploadedFile] = useState<SimpleAPIResponse>();
    const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);

    if (!useLogin) {
        throw new Error("The UploadFile component requires useLogin to be true");
    }

    const client = useMsal().instance;

    // Handler for the "Manage file uploads" button
    const handleButtonClick = async () => {
        setIsCalloutVisible(!isCalloutVisible); // Toggle the Callout visibility

        // Update uploaded files by calling the API
        try {
            const idToken = await getToken(client);
            if (!idToken) {
                throw new Error("No authentication token available");
            }
            listUploadedFilesApi(idToken).then(files => setUploadedFiles(files));
            setIsLoading(false);
        } catch (error) {
            console.error(error);
            setIsLoading(false);
        }
    };

    const handleRemoveFile = async (filename: string) => {
        try {
            const idToken = await getToken(client);
            if (!idToken) {
                throw new Error("No authentication token available");
            }
            await deleteUploadedFileApi(filename, idToken);
            const newFiles = uploadedFiles.filter(file => file !== filename);
            // To discuss: We could also poll the list endpoint here
            setUploadedFiles(newFiles);
        } catch (error) {
            console.error(error);
        }
    };

    // Handler for the form submission (file upload)
    const handleUploadFile = async (e: ChangeEvent<HTMLInputElement>) => {
        e.preventDefault();
        if (!e.target.files || e.target.files.length === 0) {
            return;
        }
        setIsUploading(true); // Start the loading state
        const file: File = e.target.files[0];
        const formData = new FormData();
        formData.append("file", file);

        try {
            const idToken = await getToken(client);
            if (!idToken) {
                throw new Error("No authentication token available");
            }
            const response: SimpleAPIResponse = await uploadFileApi(formData, idToken);
            setUploadedFile(response);
            uploadedFiles.push(file.name);
            setIsUploading(false);
        } catch (error) {
            console.error(error);
            setIsUploading(false);
        }
    };

    return (
        <div className={`${styles.container} ${className ?? ""}`}>
            <div>
                <Button className={styles.btn_action} id="calloutButton" icon={<Add24Regular />} disabled={disabled} onClick={handleButtonClick}>
                    Manage file uploads
                </Button>

                {isCalloutVisible && (
                    <Callout
                        role="dialog"
                        gapSpace={0}
                        className={styles.callout}
                        target="#calloutButton"
                        onDismiss={() => setIsCalloutVisible(false)}
                        setInitialFocus
                    >
                        <form encType="multipart/form-data">
                            <div>
                                <Label>Upload file:</Label>
                                <input
                                    accept=".txt, .md, .json, .jpg, .jpeg, .bmp, .heic, .tiff, .pdf, .docx, .xlsx, .pptx, .html"
                                    className={styles.chooseFiles}
                                    type="file"
                                    onChange={handleUploadFile}
                                />
                            </div>
                        </form>

                        {/* Show a loading message while files are being uploaded */}
                        {isUploading && <div className={styles.padding8}>{"Uploading files..."}</div>}
                        {!isUploading && uploadedFile && <div className={styles.padding8}>{uploadedFile.message}</div>}
                        {/* Display the list of already uploaded */}

                        <h3>Previously uploaded files:</h3>

                        {isLoading && <Text>Loading...</Text>}
                        {!isLoading && uploadedFiles.length === 0 && <Text>No files uploaded yet</Text>}
                        {uploadedFiles.map((filename, index) => {
                            return (
                                <div key={index} className={styles.list}>
                                    <div className={styles.item}>{filename}</div>
                                    {/* Button to remove a file from the list */}
                                    <Button
                                        className={styles.delete}
                                        onClick={() => handleRemoveFile(filename)}
                                        icon={<Delete24Regular />}
                                        title="Remove file"
                                    />
                                </div>
                            );
                        })}
                    </Callout>
                )}
            </div>
        </div>
    );
};

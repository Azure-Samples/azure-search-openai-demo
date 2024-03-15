import React, { useState, ChangeEvent, FormEvent } from "react";
import styles from "./UploadFile.module.css";
import { IIconProps, Callout, ActionButton, PrimaryButton, Label, IconButton, Text } from "@fluentui/react";
import { SimpleAPIResponse, uploadFileApi, deleteUploadedFileApi, listUploadedFilesApi } from "../../api";
import { useMsal } from "@azure/msal-react";
import { useLogin, getToken } from "../../authConfig";

interface Props {
    className?: string;
}

export const UploadFile: React.FC<Props> = ({ className }: Props) => {
    // State variables to manage the component behavior
    const [isCalloutVisible, setIsCalloutVisible] = useState<boolean>(false);
    const [isUploading, setIsUploading] = useState<boolean>(false);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [uploadedFile, setUploadedFile] = useState<SimpleAPIResponse>();
    const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);

    if (!useLogin) {
        console.error("This component requires useLogin to be true");
        return null;
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

    const addIcon: IIconProps = { iconName: "Add" };
    const Remove: IIconProps = { iconName: "delete" };

    return (
        <div className={`${styles.container} ${className ?? ""}`}>
            <div>
                <ActionButton className={styles.btn_action} id="calloutButton" iconProps={addIcon} allowDisabledFocus onClick={handleButtonClick}>
                    Manage file uploads
                </ActionButton>

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
                        {uploadedFile && <div className={styles.padding8}>{uploadedFile.message}</div>}
                        {/* Display the list of already uploaded */}

                        <h3>Previously uploaded files:</h3>

                        {isLoading && <Text>Loading...</Text>}
                        {!isLoading && uploadedFiles.length === 0 && <Text>No files uploaded yet</Text>}
                        {uploadedFiles.map((filename, index) => {
                            return (
                                <div key={index} className={styles.list}>
                                    <div className={styles.item}>{filename}</div>
                                    {/* Button to remove a file from the list */}
                                    <IconButton
                                        className={styles.delete}
                                        onClick={() => handleRemoveFile(filename)}
                                        iconProps={Remove}
                                        title="Remove file"
                                        ariaLabel="Remove file"
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

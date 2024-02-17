import { useEffect, useState, useRef } from "react";
import { useMsal } from "@azure/msal-react";
import { Stack, TextField, Icon } from "@fluentui/react";
import { Button, Tooltip, Field, Textarea } from "@fluentui/react-components";
import { Send28Filled } from "@fluentui/react-icons";
import { isLoggedIn, requireAccessControl } from "../../authConfig";

import styles from "./QuestionInput.module.css";

interface Props {
    // onSend: (question: string) => void;
    onSend: (resizedBase64Image: string) => void;
    disabled: boolean;
    initQuestion?: string;
    placeholder?: string;
    clearOnSend?: boolean;
}

export const QuestionInput = ({ onSend, disabled, placeholder, clearOnSend, initQuestion }: Props) => {
    const [question, setQuestion] = useState<string>("");
    const [uploadedImage, setUploadedImage] = useState<File | null>(null);
    const [imageUrl, setImageUrl] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        initQuestion && setQuestion(initQuestion);
    }, [initQuestion]);

    const sendQuestion = () => {
        if (disabled || (!question.trim() && imageUrl?.length === 0)) {
            return;
        }
        if (uploadedImage) {
            const reader = new FileReader();
            reader.readAsDataURL(uploadedImage);
            reader.onloadend = async () => {
                const base64Image = reader.result as string;

                // Create a temporary image element to load the uploaded image
                const tempImage = new Image();
                tempImage.src = base64Image;

                tempImage.onload = () => {
                    // Set the desired width and height for the resized image
                    const maxWidth = 800;
                    const maxHeight = 800;
                    const quality = 0.7; // Set the desired quality value between 0 and 1

                    // Calculate the new width and height while maintaining the aspect ratio
                    let newWidth = tempImage.width;
                    let newHeight = tempImage.height;
                    if (newWidth > maxWidth) {
                        const ratio = maxWidth / newWidth;
                        newWidth = maxWidth;
                        newHeight = newHeight * ratio;
                    }
                    if (newHeight > maxHeight) {
                        const ratio = maxHeight / newHeight;
                        newHeight = maxHeight;
                        newWidth = newWidth * ratio;
                    }

                    // Create a canvas element to draw the resized image
                    const canvas = document.createElement("canvas");
                    canvas.width = newWidth;
                    canvas.height = newHeight;

                    // Draw the resized image on the canvas
                    const ctx = canvas.getContext("2d");
                    if (ctx) {
                        ctx.drawImage(tempImage, 0, 0, newWidth, newHeight);
                    }

                    // Get the resized image as base64 with reduced quality
                    const resizedBase64Image = canvas.toDataURL("image/jpeg", quality);

                    // Call the onSend function with the resized base64 image
                    onSend(resizedBase64Image);
                };
            };
            // onSend(imageUrl as string);
        } else {
            onSend(question);
        }

        if (clearOnSend) {
            setQuestion("");
            setImageUrl("");
        }
    };

    const sendImage = () => {
        const reader = new FileReader();
        if (uploadedImage !== null) {
            reader.readAsDataURL(uploadedImage);
            reader.onloadend = () => {
                const base64Image = reader.result as string;

                // Create a temporary image element to load the uploaded image
                const tempImage = new Image();
                tempImage.src = base64Image;

                tempImage.onload = () => {
                    // Set the desired width and height for the resized image
                    const maxWidth = 800;
                    const maxHeight = 800;
                    const quality = 1; // Set the desired quality value between 0 and 1

                    // Calculate the new width and height while maintaining the aspect ratio
                    let newWidth = tempImage.width;
                    let newHeight = tempImage.height;
                    if (newWidth > maxWidth) {
                        const ratio = maxWidth / newWidth;
                        newWidth = maxWidth;
                        newHeight = newHeight * ratio;
                    }
                    if (newHeight > maxHeight) {
                        const ratio = maxHeight / newHeight;
                        newHeight = maxHeight;
                        newWidth = newWidth * ratio;
                    }

                    // Create a canvas element to draw the resized image
                    const canvas = document.createElement("canvas");
                    canvas.width = newWidth;
                    canvas.height = newHeight;

                    // Draw the resized image on the canvas
                    const ctx = canvas.getContext("2d");
                    if (ctx) {
                        ctx.drawImage(tempImage, 0, 0, newWidth, newHeight);
                    }

                    // Get the resized image as base64 with reduced quality
                    const resizedBase64Image = canvas.toDataURL("image/jpeg", quality);

                    // Call the onSend function with the resized base64 image
                    onSend(resizedBase64Image);
                };
            };

            // onSend(imageUrl as string);
        }
        if (clearOnSend) {
            setImageUrl("");
        }
    };
    const onEnterPress = (ev: React.KeyboardEvent<Element>) => {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            sendQuestion();
            // sendImage();
        }
    };

    const onQuestionChange = (_ev: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>, newValue?: string) => {
        if (!newValue) {
            setQuestion("");
        } else if (newValue.length <= 1000) {
            setQuestion(newValue);
            setUploadedImage(null);
            setImageUrl(null);
        }
    };

    const onImageChange = (ev: React.ChangeEvent<HTMLInputElement>) => {
        if (ev.target.files && ev.target.files.length > 0) {
            const file = ev.target.files[0];
            setUploadedImage(file);
            setImageUrl(URL.createObjectURL(file));
            setQuestion("");
        }
    };

    const onImageClear = () => {
        setUploadedImage(null);
        setImageUrl(null);
        fileInputRef.current && (fileInputRef.current.value = "");
    };

    const { instance } = useMsal();
    const disableRequiredAccessControl = requireAccessControl && !isLoggedIn(instance);
    const sendQuestionDisabled = disabled || disableRequiredAccessControl || (!question.trim() && imageUrl?.length === 0);
    const sendImageDisabled = disabled || disableRequiredAccessControl || imageUrl?.length === 0;

    if (disableRequiredAccessControl) {
        placeholder = "Please login to continue...";
    }

    return (
        <Stack tokens={{ childrenGap: 10 }}>
            <Stack horizontal className={styles.questionInputContainer}>
                <Stack tokens={{ childrenGap: 10 }} className={styles.imageInputContainer}>
                    <Stack.Item>
                        <input type="file" accept="image/*" ref={fileInputRef} onChange={onImageChange} disabled={disabled} hidden />
                        {/* <Tooltip relationship={"label"} content="Upload image"> */}
                        <Button onClick={() => fileInputRef.current && fileInputRef.current.click()} disabled={disabled} className={styles.uploadButton}>
                            <Icon iconName="FileImage" />
                        </Button>
                        {/* </Tooltip> */}
                    </Stack.Item>
                </Stack>

                <TextField
                    className={styles.questionInputTextArea}
                    disabled={disableRequiredAccessControl}
                    placeholder={placeholder}
                    multiline
                    resizable={false}
                    borderless
                    value={question}
                    onChange={onQuestionChange}
                    onKeyDown={onEnterPress}
                />
                <div className={styles.questionInputButtonsContainer}>
                    {/* <Tooltip content="Ask question button" relationship="label"> */}
                    <Button
                        size="large"
                        icon={<Send28Filled primaryFill="rgba(115, 118, 225, 1)" />}
                        disabled={sendQuestionDisabled}
                        onClick={sendQuestion}
                        // disabled={sendImageDisabled}
                        // onClick={sendImage}
                    />
                    {/* </Tooltip> */}
                </div>
            </Stack>
            {imageUrl && (
                <Button className={styles.removeButton} onClick={onImageClear} disabled={disabled}>
                    <img src={imageUrl} alt="Image" className={styles.imageButton} />
                    <Icon iconName="Cancel" className={styles.removeIcon} />
                </Button>
            )}
        </Stack>
    );
};

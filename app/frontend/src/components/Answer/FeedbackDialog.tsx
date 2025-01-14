import React from "react";
import { Dialog, DialogType, TextField, DefaultButton, PrimaryButton, Stack } from "@fluentui/react";

interface FeedbackDialogProps {
    isOpen: boolean;
    value: number;
    onDismiss: () => void;
    onSubmit: (comment: string) => void;
}

export const FeedbackDialog: React.FC<FeedbackDialogProps> = ({ isOpen, value, onDismiss, onSubmit }) => {
    const [comment, setComment] = React.useState("");

    const handleSubmit = () => {
        onSubmit(comment);
        setComment(""); // Reset comment after submission
    };

    return (
        <Dialog
            hidden={!isOpen}
            onDismiss={onDismiss}
            dialogContentProps={{
                type: DialogType.normal,
                title: value === 1 ? "Positive Feedback" : "Negative Feedback"
            }}
            modalProps={{
                isBlocking: false,
                styles: { main: { maxWidth: 450 } }
            }}
        >
            <Stack tokens={{ childrenGap: 20 }}>
                <TextField
                    multiline
                    rows={3}
                    value={comment}
                    onChange={(_, newValue) => setComment(newValue || "")}
                    placeholder="Comments (optional)"
                    label="Enter your feedback"
                />
                <Stack horizontal tokens={{ childrenGap: 10 }} horizontalAlign="end">
                    <DefaultButton onClick={() => onSubmit("")} text="Skip Comment" />
                    <PrimaryButton onClick={handleSubmit} text="Submit" disabled={!comment.trim()} />
                </Stack>
            </Stack>
        </Dialog>
    );
};

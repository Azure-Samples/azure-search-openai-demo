import React from "react";
import { PrimaryButton, Stylesheet } from "@fluentui/react";
import "./FeedbackButton.css";

const FeedbackButton = () => {
    const url = "https://ai-activator.circle.so/c/open-feedback-questions/";

    return (
        <a href={url}>
            <PrimaryButton id="FeedbackButton">Feedback</PrimaryButton>
        </a>
    );
};

export default FeedbackButton;

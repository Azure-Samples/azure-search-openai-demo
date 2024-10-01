import React from "react";
import "./Modal.css";

interface Modal {
    onClose: () => void;
}

const DisclaimerModal: React.FC<Modal> = ({ onClose }) => {
    return (
        <div className="modal-overlay">
            <div className="modal-content">
                <h2>GovGPT Pilot</h2>
                <p>GovGPT allows you to query New Zealand government websites in an easy and convient way.</p>
                <p>
                    This product is built on top Microsoft's Azure AI platform to assist with business inquireies and is aligned with the city's AI principles.
                </p>
                <p>
                    As a proof of concept product still being tested, it may occasionally provide incomplete or inaccurate responses. Verify information with
                    links provided after the response or by visiting the relevant ministry's website. Do not use its responses as a legal or professional adivce
                    nor provide sensitive information to the chatbot.
                </p>
                <button className="modal-button" onClick={onClose}>
                    Accept
                </button>
            </div>
        </div>
    );
};

export default DisclaimerModal;

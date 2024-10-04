import * as React from "react";
import { Dialog, DialogSurface, DialogTitle, DialogContent, DialogBody, DialogActions, Button } from "@fluentui/react-components";
import "./Modal.css";

export const DisclaimerModal: React.FC = () => {
    const [open, setOpen] = React.useState(true);

    return (
        <Dialog open={open} onOpenChange={(event, data) => setOpen(data.open)} modalType="alert">
            <DialogSurface id="my-dialog-surface" className="dialog-surface">
                <DialogBody>
                    <DialogTitle id="custom-dialog-title">GovGPT - Pilot</DialogTitle>
                    <DialogContent>
                        <p>
                            <b>*This is placeholder text*</b>
                        </p>
                        <p>GovGPT allows you to query New Zealand government websites in an easy and convient way.</p>
                        <p>
                            This product is built on top Microsoft's Azure AI platform to assist with business enquireies and is aligned with the city's AI
                            principles.
                        </p>
                        <p>
                            As a proof of concept product still being tested, it may occasionally provide incomplete or inaccurate responses. Verify information
                            with links provided after the response or by visiting the relevant ministry's website. <b>Do not</b> use its responses as a legal or
                            professional adivce nor provide sensitive information to the chatbot.
                        </p>
                    </DialogContent>
                    <DialogActions>
                        <Button className="tcmodal-button" onClick={() => setOpen(false)}>
                            Accept
                        </Button>
                    </DialogActions>
                </DialogBody>
            </DialogSurface>
        </Dialog>
    );
};

export default DisclaimerModal;

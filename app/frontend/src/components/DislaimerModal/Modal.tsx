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
                            <b>IMPORTANT TERMS OF USE FOR GOVGPT</b>
                        </p>
                        <p>
                            <b>11 October 2024</b>
                        </p>
                        <p>Callaghan Innovation (we) have developed the GovGPT pilot to facilitate easier access to government-provided information.</p>
                        <p>
                            GovGPT is available to you for free. The information that GovGPT draws from is limited to selected government agencies’ websites and
                            therefore responses will only be as accurate as those websites. We do not verify the accuracy of the content on those websites. It
                            is important to note that GovGPT does not provide advice or offer viewpoint on behalf of the NZ Government.
                        </p>
                        <p>
                            GovGPT is still in a pilot phase. GovGPT may not always be available. While our aim is that GovGPT provides useful information,
                            responses may not always be accurate and may not reflect correct, current or complete information. We are not liable for any errors
                            in the responses you receive, and you should not rely on any response without independently confirming its accuracy.
                        </p>
                        <p>
                            Any information you input into GovGPT is deleted once you end your chat or session on GovGPT. Your history of inputs and GovGPT’s
                            responses are not retained beyond your current session. Despite this, we recommend that you do not input any personal information,
                            confidential or commercially sensitive information into GovGPT as a matter of best practice. You are solely responsible for any and
                            all inputs that you provide to GovGPT.
                        </p>
                        <p>
                            You must not use GovGPT in any way that causes, or may cause, damage to GovGPT, or impairs the availability or accessibility of
                            GovGPT.{" "}
                        </p>
                        <p>
                            You must not use GovGPT in any way, or for a purpose, which is unlawful, malicious, fraudulent, deceptive, abusive, offensive,
                            discriminatory or harmful. To the maximum extent permitted by law, we will not be liable to you for your use of GovGPT or for any
                            actions or outcomes that may result from your use of GovGPT. Callaghan Innovation does not guarantee the accuracy or reliability of
                            generated content. If you are using GovGPT for business use and you are in trade, you agree that these terms are the entire
                            agreement between you and us for your use of GovGPT, and that you contract out of sections 9, 12A and 13 of the Fair Trading Act
                            1986. These terms are governed by the laws of New Zealand.
                        </p>
                        <p>We may update these terms of use at any time by way of a pop-up notice.</p>
                        <p>
                            <b>
                                By [clicking I ACCEPT], you accept these terms of use. If you do not accept these terms of use, please do not click or access
                                GovGPT.
                            </b>
                        </p>
                        <p>For more information on GovGPT, see our Frequently Asked Questions.</p>
                    </DialogContent>
                    <DialogActions>
                        <Button className="tcmodal-button" onClick={() => setOpen(false)}>
                            I Accept
                        </Button>
                    </DialogActions>
                </DialogBody>
            </DialogSurface>
        </Dialog>
    );
};

export default DisclaimerModal;

// src/components/SessionModal.js

import React, {ChangeEvent, useState} from 'react';
import { Modal, Button, Form } from 'react-bootstrap';

interface SessionModalProps {
    show: boolean;
    handleClose: () => void;
    handleCreateSession: (input: string) => void;
}
export function ChatHistorySessionModal(props: SessionModalProps) {
    const show = props.show;
    const handleClose = props.handleClose;
    const handleCreateSession = props.handleCreateSession;
    const [sessionName, setSessionName] = useState<string>('');

    const handleSessionNameChange = (e: ChangeEvent<HTMLInputElement>) => {
        setSessionName(e.target.value);
    };

    const handleCreateClick = () => {
        if (sessionName.trim() === '') {
            alert('Please enter a valid session name.');
        } else {
            handleCreateSession(sessionName);
            setSessionName("")
            handleClose();
        }
    };

    return (
        <Modal show={show} onHide={handleClose}>
            <Modal.Body>
                <Form.Group controlId="sessionName">
                    <Form.Label>Session Name</Form.Label>
                    <Form.Control
                        type="text"
                        placeholder="Enter session name"
                        value={sessionName}
                        onChange={handleSessionNameChange}
                    />
                </Form.Group>
            </Modal.Body>
            <p>    </p>
            <Modal.Footer>
                <Button variant="secondary" onClick={handleClose}>
                    Close
                </Button>
                <Button style={{"marginLeft": "10px"}} variant="primary" onClick={handleCreateClick}>
                    Create
                </Button>
            </Modal.Footer>
        </Modal>
    );
}

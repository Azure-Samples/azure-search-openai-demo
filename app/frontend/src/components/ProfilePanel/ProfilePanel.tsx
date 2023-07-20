// @ts-nocheck
import React, { useState } from "react";
import { TextField, Checkbox, Slider, PrimaryButton } from "@fluentui/react";

interface Props {
    className: string;
}

export const ProfilePanel = ({ className }: Props, setProfile?: void) => {
    const [existingCustomer, setExistingCustomer] = useState(false);
    const [name, setName] = useState("");
    const [familyType, setFamilyType] = useState("");
    const [coverType, setCoverType] = useState("");
    const [ages, setAges] = useState("");
    const [budget, setBudget] = useState<[number, number]>([10, 40]);
    const [notes, setNotes] = useState("");

    const handleExistingCustomerChange = (_ev?: React.FormEvent, newValue?: boolean) => {
        setExistingCustomer(newValue ?? false);
    };

    const handleNameChange = (_ev?: React.FormEvent, newValue?: string) => {
        setName(newValue ?? "");
    };

    const handleFamilyTypeChange = (event: React.FormEvent, newValue?: string) => {
        setFamilyType(newValue ?? "");
    };

    const handleCoverTypeChange = (event: React.FormEvent, newValue?: string) => {
        setCoverType(newValue ?? "");
    };

    const handleAgesChange = (event: React.FormEvent, newValue?: string) => {
        setAges(newValue ?? "");
    };

    const handleBudgetChange = (values: [number, number]) => {
        setBudget(values);
    };

    const handleNotesChange = (event: React.FormEvent, newValue?: string) => {
        setNotes(newValue ?? "");
    };

    const handleGenerateProfile = () => {
        setProfile({
            existingCustomer,
            name,
            familyType,
            coverType,
            ages,
            budget,
            notes
        });
    };

    return (
        <div>
            <Checkbox label="Existing Customer" checked={existingCustomer} onChange={handleExistingCustomerChange} />
            <TextField label="Name" value={name} onChange={handleNameChange} />
            <TextField label="Family Type" value={familyType} onChange={handleFamilyTypeChange} />
            <TextField label="Cover Type" value={coverType} onChange={handleCoverTypeChange} />
            <TextField label="Age(s)" value={ages} onChange={handleAgesChange} />
            <br />
            <Slider ranged label="Budget" min={0} max={200} defaultValue={40} defaultLowerValue={10} onChange={handleBudgetChange} />
            <TextField label="Notes" multiline rows={5} value={notes} onChange={handleNotesChange} />
            <br />
            <PrimaryButton text="Set Profile" onClick={handleGenerateProfile} allowDisabledFocus />
        </div>
    );
};

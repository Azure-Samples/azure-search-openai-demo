// @ts-nocheck
import React, { useState } from "react";
import { TextField, Checkbox, Slider, PrimaryButton } from "@fluentui/react";

export const ProfilePanel = ({ className, setProfile }: Props) => {
    const [existingCustomer, setExistingCustomer] = useState(false);
    const [budget, setBudget] = useState<[number, number]>([10, 40]);
    const [notes, setNotes] = useState("");
    const [levelOfCover, setLevelOfCover] = useState("");
    const [scale, setScale] = useState("");
    const [state, setState] = useState("");
    const [geography, setGeography] = useState("");
    const [category, setCategory] = useState("");
    const [frequency, setFrequency] = useState("monthly");

    const handleExistingCustomerChange = (_ev?: React.FormEvent, newValue?: boolean) => {
        setExistingCustomer(newValue ?? false);
    };

    const handleBudgetChange = (values, range) => {
        setBudget(range);
        const string = `$${range[0]} - $${range[1]}`;
        handleProfileChange({ budget: string });
    };

    const handleNotesChange = (event: React.FormEvent, newValue?: string) => {
        setNotes(newValue ?? "");
        handleProfileChange({ notes: newValue ?? "" });
    };

    const handleLevelOfCoverChange = (event: React.FormEvent, newValue?: string) => {
        setLevelOfCover(newValue ?? "");
        handleProfileChange({ levelOfCover: newValue ?? "" });
    };

    const handleScaleChange = (event: React.FormEvent, newValue?: string) => {
        setScale(newValue ?? "");
        handleProfileChange({ scale: newValue ?? "" });
    };

    const handleStateChange = (event: React.FormEvent, newValue?: string) => {
        setState(newValue ?? "");
        handleProfileChange({ state: newValue ?? "" });
    };

    const handleGeographyChange = (event: React.FormEvent, newValue?: string) => {
        setGeography(newValue ?? "");
        handleProfileChange({ geography: newValue ?? "" });
    };

    const handleCategoryChange = (event: React.FormEvent, newValue?: string) => {
        setCategory(newValue ?? "");
        handleProfileChange({ category: newValue ?? "" });
    };

    const handleFrequencyChange = (event: React.FormEvent, newValue?: string) => {
        setFrequency(newValue ?? "");
        handleProfileChange({ frequency: newValue ?? "" });
    };

    const handleProfileChange = field => {
        const currentProfile = {
            existingCustomer,
            budget,
            notes,
            levelOfCover,
            scale,
            state,
            geography,
            category,
            frequency
        };
        setProfile({ ...currentProfile, ...field });
    };

    return (
        <div>
            <br />
            <Checkbox label="Existing Customer" checked={existingCustomer} onChange={handleExistingCustomerChange} />
            <TextField label="Level of Cover" value={levelOfCover} onChange={handleLevelOfCoverChange} placeholder="Enter level of cover" />
            <TextField label="Scale" value={scale} onChange={handleScaleChange} placeholder="Single, Family, Single Parents" />
            <TextField label="State" value={state} onChange={handleStateChange} placeholder="NSW, TAS etc" />
            <TextField label="Geography" value={geography} placeholder="Enter geography (e.g., international, retail, etc.)" onChange={handleGeographyChange} />
            <TextField label="Category" value={category} onChange={handleCategoryChange} placeholder="Hospital, Hospital Extras" />
            <br />
            <Slider ranged label="Budget" min={0} max={300} defaultValue={300} defaultLowerValue={10} onChange={handleBudgetChange} />
            <TextField label="Frequency" value={frequency} onChange={handleFrequencyChange} placeholder="Monthly, Fortnightly, Weekly" />
            <TextField label="Notes" multiline rows={5} value={notes} onChange={handleNotesChange} placeholder="Medical history, or upcoming operations " />
        </div>
    );
};

import React, { useState } from "react";
import { TextField, Dropdown, PrimaryButton, IDropdownOption, DropdownMenuItemType } from "@fluentui/react";

interface Props {
    className: string;
    setFilter: () => void;
}

const lifeCycleOptions: IDropdownOption[] = [
    { key: "OnSale", text: "OnSale" },
    { key: "OffSale", text: "OffSale" }
];

const stateOptions: IDropdownOption[] = [
    { key: "", text: "None" },
    { key: "ACT", text: "Australian Capital Territory" },
    { key: "NSW", text: "New South Wales" },
    { key: "NT", text: "Northern Territory" },
    { key: "QLD", text: "Queensland" },
    { key: "SA", text: "South Australia" },
    { key: "TAS", text: "Tasmania" },
    { key: "VIC", text: "Victoria" },
    { key: "WA", text: "Western Australia" }
];

export const FilterPanel = ({ className }: Props, setProfile?: void) => {
    const [familyType, setFamilyType] = useState("");
    const [coverType, setCoverType] = useState("");
    const [state, setState] = useState("");
    const [lifecycle, setLifecycle] = useState("");

    const handleFamilyTypeChange = (event: React.FormEvent, newValue?: string) => {
        setFamilyType(newValue ?? "");
    };

    const handleCoverTypeChange = (event: React.FormEvent, newValue?: string) => {
        setCoverType(newValue ?? "");
    };

    const handleStateChange = (event: React.FormEvent, newValue?: string) => {
        setState(newValue ?? "");
    };

    const handleLifecycleChange = (event: React.FormEvent, newValue?: string) => {
        setLifecycle(newValue ?? "");
    };

    const handleGenerateProfile = () => {
        setFilter({
            familyType,
            coverType,
            state
        });
    };

    return (
        <div>
            <TextField label="Family Type" value={familyType} onChange={handleFamilyTypeChange} />
            <TextField label="Product" value={coverType} onChange={handleCoverTypeChange} />
            <Dropdown placeholder="Select State" label="State" options={stateOptions} onChange={handleStateChange} />
            <Dropdown placeholder="Set lifecycle" label="Lifecycle" options={lifeCycleOptions} onChange={handleLifecycleChange} />
            <br />
            <PrimaryButton text="Set Filter" onClick={handleGenerateProfile} allowDisabledFocus />
        </div>
    );
};

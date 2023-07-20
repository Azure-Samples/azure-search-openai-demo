// @ts-nocheck
import React, { useState } from "react";
import { TextField, Dropdown, PrimaryButton, IDropdownOption, DropdownMenuItemType } from "@fluentui/react";
import { FilterSettings } from "../../pages/chat/Chat";

interface Props {
    className: string;
    onSetFilter: (filter: FilterSettings) => void;
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

export const FilterPanel = ({ className, onSetFilter, onQueryPromptChange, defaultQuery }: Props) => {
    const [familyType, setFamilyType] = useState("");
    const [productType, setProductType] = useState("");
    const [state, setState] = useState("");
    const [lifecycle, setLifecycle] = useState("");

    const handleProfileChange = field => {
        const currentFilters = {
            familyType,
            productType,
            stateType: state.key,
            lifecycle: lifecycle.key
        };
        onSetFilter({ ...currentFilters, field });
    };

    const handleFamilyTypeChange = (event: React.FormEvent, newValue?: string) => {
        setFamilyType(newValue ?? "");
        handleProfileChange({ familyType: newValue });
    };

    const handleProductTypeChange = (event: React.FormEvent, newValue?: string) => {
        setProductType(newValue ?? "");
        handleProfileChange({ productType: newValue });
    };

    const handleStateChange = (event: React.ChangeEvent<HTMLSelectElement>, newValue?: string) => {
        setState(newValue ?? "");
        handleProfileChange({ stateType: newValue });
    };

    const handleLifecycleChange = (event: React.ChangeEvent<HTMLSelectElement>, newValue?: string) => {
        setLifecycle(newValue ?? "");
        handleProfileChange({ lifecycle: newValue });
    };

    return (
        <div>
            <TextField label="Family Type" value={familyType} onChange={handleFamilyTypeChange} />
            <TextField label="Product" value={productType} onChange={handleProductTypeChange} />
            <Dropdown placeholder="Select State" label="State" options={stateOptions} onChange={handleStateChange} />
            <Dropdown placeholder="Set lifecycle" label="Lifecycle" options={lifeCycleOptions} onChange={handleLifecycleChange} />
            <br />
            <TextField defaultValue={defaultQuery} label="Query prompt" multiline rows={20} autoAdjustHeight onChange={onQueryPromptChange} />
        </div>
    );
};

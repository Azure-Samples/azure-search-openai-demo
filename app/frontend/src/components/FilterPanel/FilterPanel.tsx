// @ts-nocheck
import React, { useState } from "react";
import { TextField, Dropdown, PrimaryButton, IDropdownOption, DropdownMenuItemType } from "@fluentui/react";
import { FilterSettings } from "../../pages/chat/Chat";

interface Props {
    className: string;
    onSetFilter: (filter: FilterSettings) => void;
}

const lifeCycleOptions: IDropdownOption[] = [
    { key: "", text: "None" },
    { key: "OnSale", text: "OnSale" },
    { key: "OffSale", text: "OffSale" }
];

const stateOptions: IDropdownOption[] = [
    { key: "", text: "None" },
    { key: "Act", text: "Australian Capital Territory" },
    { key: "Nsw", text: "New South Wales" },
    { key: "Nt", text: "Northern Territory" },
    { key: "Qld", text: "Queensland" },
    { key: "Sa", text: "South Australia" },
    { key: "Tas", text: "Tasmania" },
    { key: "Vic", text: "Victoria" },
    { key: "Wa", text: "Western Australia" }
];

export const FilterPanel = ({
    className,
    onSetFilter,
    onQueryPromptChange,
    defaultQuery,
    onSearchTempratureChange,
    searchTemperature,
    searchTokens,
    onSearchTokensChange
}: Props) => {
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
        onSetFilter({ ...currentFilters, ...field });
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
        handleProfileChange({ stateType: newValue.key });
    };

    const handleLifecycleChange = (event: React.ChangeEvent<HTMLSelectElement>, newValue?: string) => {
        setLifecycle(newValue ?? "");
        handleProfileChange({ lifecycle: newValue.key });
    };

    return (
        <div>
            <TextField label="Family Type" value={familyType} onChange={handleFamilyTypeChange} placeholder="e.g. Couple, Family, SingleParentPlus" />
            <TextField label="Product" value={productType} onChange={handleProductTypeChange} placeholder="e.g. Start 'n' Save - Gold" />
            <Dropdown placeholder="Select State" label="State" options={stateOptions} onChange={handleStateChange} />
            <Dropdown placeholder="Set lifecycle" label="Lifecycle" options={lifeCycleOptions} onChange={handleLifecycleChange} />
            <br />
            <TextField label="Search Max Tokens" value={searchTokens} onChange={onSearchTokensChange} />
            <TextField label="Search Temprature" value={searchTemperature} onChange={onSearchTempratureChange} />
            <TextField defaultValue={defaultQuery} label="Query prompt" multiline rows={20} autoAdjustHeight onChange={onQueryPromptChange} />
        </div>
    );
};

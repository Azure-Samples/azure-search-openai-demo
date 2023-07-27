// @ts-nocheck
import React, { useState } from "react";
import { TextField, Dropdown, IDropdownOption } from "@fluentui/react";
import { FilterSettings } from "../../pages/chat/Chat";

interface Props {
    className: string;
    onSetFilter: (filter: FilterSettings) => void;
}

const lifeCycleOptions: IDropdownOption[] = [
    { key: "", text: "Any" },
    { key: "OnSale", text: "OnSale" },
    { key: "OffSale", text: "OffSale" }
];

const stateOptions: IDropdownOption[] = [
    { key: "", text: "Any" },
    { key: "Act", text: "Australian Capital Territory" },
    { key: "Nsw", text: "New South Wales" },
    { key: "Nt", text: "Northern Territory" },
    { key: "Qld", text: "Queensland" },
    { key: "Sa", text: "South Australia" },
    { key: "Tas", text: "Tasmania" },
    { key: "Vic", text: "Victoria" },
    { key: "Wa", text: "Western Australia" }
];

const productNameOptions: IDropdownOption[] = [
    { key: "", text: "Any" },
    { key: "Corporate Benefit 80", text: "Corporate Benefit 80" },
    { key: "Corporate Bronze Plus Hospital $250 Excess", text: "Corporate Bronze Plus Hospital $250 Excess" },
    { key: "Corporate Bronze Plus Hospital $500 Excess", text: "Corporate Bronze Plus Hospital $500 Excess" },
    { key: "Corporate Bronze Plus Hospital $750 Excess", text: "Corporate Bronze Plus Hospital $750 Excess" },
    { key: "Essential 50 Visitors Hospital Cover", text: "Essential 50 Visitors Hospital Cover" },
    { key: "Essential Extras", text: "Essential Extras" },
    { key: "FLEXtras 4 Standard 60", text: "FLEXtras 4 Standard 60" },
    { key: "Gold Ultimate Health Hospital Cover", text: "Gold Ultimate Health Hospital Cover" },
    { key: "Premium Ambulance", text: "Premium Ambulance" },
    { key: "Premium Visitors Cover with Excess", text: "Premium Visitors Cover with Excess" },
    { key: "Simple Start Hospital - Basic Plus", text: "Simple Start Hospital - Basic Plus" },
    { key: "Start 'n' Save - Gold", text: "Start 'n' Save - Gold" }
];

const familyTypeOptions: IDropdownOption[] = [
    { key: "", text: "Any" },
    { key: "Single", text: "Single" },
    { key: "Couple", text: "Couple" },
    { key: "Family", text: "Family" },
    { key: "SingleParent", text: "Single Parent" },
    { key: "SingleParentPlus", text: "Single Parent Plus" },
    { key: "FamilyPlus", text: "Family Plus" }
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
    const [productName, setProductName] = useState("");
    const [state, setState] = useState("");
    const [lifecycle, setLifecycle] = useState("");

    const handleProfileChange = field => {
        const currentFilters = {
            familyType: familyType.key,
            productName: productName.key,
            stateType: state.key,
            lifecycle: lifecycle.key
        };
        onSetFilter({ ...currentFilters, ...field });
    };

    const handleStateChange = (event: React.ChangeEvent<HTMLSelectElement>, newValue?: string) => {
        setState(newValue ?? "");
        handleProfileChange({ stateType: newValue.key });
    };

    const handleLifecycleChange = (event: React.ChangeEvent<HTMLSelectElement>, newValue?: string) => {
        setLifecycle(newValue ?? "");
        handleProfileChange({ lifecycle: newValue.key });
    };

    const handleFamilyChange = (event: React.ChangeEvent<HTMLSelectElement>, newValue?: string) => {
        setFamilyType(newValue ?? "");
        handleProfileChange({ familyType: newValue.key });
    };

    const handleProductChange = (event: React.ChangeEvent<HTMLSelectElement>, newValue?: string) => {
        setProductName(newValue ?? "");
        handleProfileChange({ productName: newValue.key });
    };

    return (
        <div>
            <Dropdown placeholder="Select Family Type" label="Family Type" options={familyTypeOptions} onChange={handleFamilyChange} />
            <Dropdown placeholder="Select Product Name" label="Product" options={productNameOptions} onChange={handleProductChange} />
            <Dropdown placeholder="Select State" label="State" options={stateOptions} onChange={handleStateChange} />
            <Dropdown placeholder="Set lifecycle" label="Lifecycle" options={lifeCycleOptions} onChange={handleLifecycleChange} />
            <br />
            <TextField label="Search Max Tokens" value={searchTokens} onChange={onSearchTokensChange} />
            <TextField label="Search Temprature" value={searchTemperature} onChange={onSearchTempratureChange} />
            <TextField defaultValue={defaultQuery} label="Query prompt" multiline rows={20} autoAdjustHeight onChange={onQueryPromptChange} />
        </div>
    );
};

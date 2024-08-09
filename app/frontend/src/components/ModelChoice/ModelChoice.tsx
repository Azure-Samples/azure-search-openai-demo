import { useEffect, useState } from "react";
import { Stack, IDropdownOption, Dropdown, IDropdownProps } from "@fluentui/react";
import { useId } from "@fluentui/react-hooks";

import { HelpCallout } from "../HelpCallout";
import { toolTipText } from "../../i18n/tooltips.js";

interface Props {
    defaultModel: string;
    modelsList: string[];
    updateCurrentModel: (model: string) => void;
}

export const ModelChoice = ({ updateCurrentModel, defaultModel: defaultModel, modelsList }: Props) => {
    const [model, setModel] = useState<string>(defaultModel);

    const onModelChange = (_ev: React.FormEvent<HTMLDivElement>, option?: IDropdownOption<string> | undefined) => {
        const newModel = option?.key as string;
        setModel(newModel);
        updateCurrentModel(newModel);
    };

    const modelId = useId("model");
    const modelFieldId = useId("modelFieldId");
    const modelsMapping = modelsList.map(model => ({
        key: model,
        text: model
    }));

    return (
        <Stack tokens={{ childrenGap: 10 }}>
            <Dropdown
                id={modelFieldId}
                label="Model"
                selectedKey={model}
                options={modelsMapping}
                required
                onChange={onModelChange}
                aria-labelledby={modelId}
                onRenderLabel={(props: IDropdownProps | undefined) => (
                    <HelpCallout labelId={modelId} fieldId={modelFieldId} helpText={toolTipText.model} label={props?.label} />
                )}
            />
        </Stack>
    );
};

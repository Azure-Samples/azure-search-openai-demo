import { useEffect, useState } from "react";
import { Stack, Checkbox, ICheckboxProps, IDropdownOption, IDropdownProps, Dropdown } from "@fluentui/react";
import { useId } from "@fluentui/react-hooks";

import styles from "./GPT4VSettings.module.css";
import { GPT4VInput } from "../../api";
import { HelpCallout } from "../../components/HelpCallout";
import { toolTipText } from "../../i18n/tooltips.js";

interface Props {
    gpt4vInputs: GPT4VInput;
    isUseGPT4V: boolean;
    updateGPT4VInputs: (input: GPT4VInput) => void;
    updateUseGPT4V: (useGPT4V: boolean) => void;
}

export const GPT4VSettings = ({ updateGPT4VInputs, updateUseGPT4V, isUseGPT4V, gpt4vInputs }: Props) => {
    const [useGPT4V, setUseGPT4V] = useState<boolean>(isUseGPT4V);
    const [vectorFieldOption, setVectorFieldOption] = useState<GPT4VInput>(gpt4vInputs || GPT4VInput.TextAndImages);

    const onuseGPT4V = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        updateUseGPT4V(!!checked);
        setUseGPT4V(!!checked);
    };

    const onSetGPT4VInput = (_ev: React.FormEvent<HTMLDivElement>, option?: IDropdownOption<GPT4VInput> | undefined) => {
        if (option) {
            const data = option.key as GPT4VInput;
            updateGPT4VInputs(data || GPT4VInput.TextAndImages);
            data && setVectorFieldOption(data);
        }
    };

    useEffect(() => {
        useGPT4V && updateGPT4VInputs(GPT4VInput.TextAndImages);
    }, [useGPT4V]);

    const useGPT4VId = useId("useGPT4V");
    const gpt4VInputId = useId("gpt4VInput");

    return (
        <Stack className={styles.container} tokens={{ childrenGap: 10 }}>
            <Checkbox
                checked={useGPT4V}
                label="Use GPT-4 Turbo with Vision"
                onChange={onuseGPT4V}
                aria-labelledby={useGPT4VId}
                onRenderLabel={(props: ICheckboxProps | undefined) => <HelpCallout id={useGPT4VId} helpText={toolTipText.useGPT4Vision} label={props?.label} />}
            />
            {useGPT4V && (
                <Dropdown
                    selectedKey={vectorFieldOption}
                    label="GPT-4 Turbo with Vision inputs"
                    options={[
                        {
                            key: GPT4VInput.TextAndImages,
                            text: "Images and text"
                        },
                        { text: "Images", key: GPT4VInput.Images },
                        { text: "Text", key: GPT4VInput.Texts }
                    ]}
                    required
                    onChange={onSetGPT4VInput}
                    aria-labelledby={gpt4VInputId}
                    onRenderLabel={(props: IDropdownProps | undefined) => (
                        <HelpCallout id={gpt4VInputId} helpText={toolTipText.gpt4VisionInputs} label={props?.label} />
                    )}
                />
            )}
        </Stack>
    );
};

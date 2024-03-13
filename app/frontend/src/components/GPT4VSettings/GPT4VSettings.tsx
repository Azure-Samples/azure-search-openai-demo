import { useEffect, useState } from "react";
import { Stack, Checkbox, IDropdownOption, Dropdown } from "@fluentui/react";

import styles from "./GPT4VSettings.module.css";
import { GPT4VInput } from "../../api";

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

    return (
        <Stack className={styles.container} tokens={{ childrenGap: 10 }}>
            <Checkbox checked={useGPT4V} label="Use GPT-4 Turbo with Vision" onChange={onuseGPT4V} />
            {useGPT4V && (
                <Dropdown
                    selectedKey={vectorFieldOption}
                    label="GPT-4 Turbo with Vision Inputs"
                    options={[
                        {
                            key: GPT4VInput.TextAndImages,
                            text: "Images and text from index"
                        },
                        { text: "Images only", key: GPT4VInput.Images },
                        { text: "Text only", key: GPT4VInput.Texts }
                    ]}
                    required
                    onChange={onSetGPT4VInput}
                />
            )}
        </Stack>
    );
};

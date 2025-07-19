import { ITextFieldProps, DefaultButton, IconButton, IButtonStyles, Callout, IStackTokens, Stack, IStackStyles, initializeIcons } from "@fluentui/react";
import { useBoolean, useId } from "@fluentui/react-hooks";
import { useTranslation } from "react-i18next";

const stackTokens: IStackTokens = {
    childrenGap: 4,
    maxWidth: 300
};

const labelCalloutStackStyles: Partial<IStackStyles> = { root: { padding: 20 } };
const iconButtonStyles: Partial<IButtonStyles> = { root: { marginBottom: -3 } };
const iconProps = { iconName: "Info" };

interface IHelpCalloutProps {
    label: string | undefined;
    labelId: string;
    fieldId: string | undefined;
    helpText: string;
}

export const HelpCallout = (props: IHelpCalloutProps): JSX.Element => {
    const [isCalloutVisible, { toggle: toggleIsCalloutVisible }] = useBoolean(false);
    const descriptionId: string = useId("description");
    const iconButtonId: string = useId("iconButton");
    const { t } = useTranslation();

    return (
        <>
            <Stack horizontal verticalAlign="center" tokens={stackTokens}>
                <label id={props.labelId} htmlFor={props.fieldId}>
                    {props.label}
                </label>
                <IconButton
                    id={iconButtonId}
                    iconProps={iconProps}
                    title={t("tooltips.info")}
                    ariaLabel={t("tooltips.info")}
                    onClick={toggleIsCalloutVisible}
                    styles={iconButtonStyles}
                />
            </Stack>
            {isCalloutVisible && (
                <Callout target={"#" + iconButtonId} setInitialFocus onDismiss={toggleIsCalloutVisible} ariaDescribedBy={descriptionId} role="alertdialog">
                    <Stack tokens={stackTokens} horizontalAlign="start" styles={labelCalloutStackStyles}>
                        <span id={descriptionId}>{props.helpText}</span>
                        <DefaultButton onClick={toggleIsCalloutVisible}>{t("labels.closeButton")}</DefaultButton>
                    </Stack>
                </Callout>
            )}
        </>
    );
};

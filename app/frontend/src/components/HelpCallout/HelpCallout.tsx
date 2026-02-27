import { type JSX, useId, useState } from "react";
import { Button, Popover, PopoverTrigger, PopoverSurface } from "@fluentui/react-components";
import { Info24Regular } from "@fluentui/react-icons";
import { useTranslation } from "react-i18next";

interface IHelpCalloutProps {
    label: string | undefined;
    labelId: string;
    fieldId: string | undefined;
    helpText: string;
}

export const HelpCallout = (props: IHelpCalloutProps): JSX.Element => {
    const [isCalloutVisible, setIsCalloutVisible] = useState(false);
    const descriptionId = useId();
    const { t } = useTranslation();

    return (
        <>
            <div style={{ display: "flex", alignItems: "center", gap: "4px", flex: 1 }}>
                <label id={props.labelId} htmlFor={props.fieldId}>
                    {props.label}
                </label>
                <Popover open={isCalloutVisible} onOpenChange={(_e, data) => setIsCalloutVisible(data.open)} trapFocus>
                    <PopoverTrigger disableButtonEnhancement>
                        <Button
                            appearance="transparent"
                            icon={<Info24Regular />}
                            title={t("tooltips.info")}
                            aria-label={t("tooltips.info")}
                            style={{ marginBottom: -3, flexShrink: 0 }}
                        />
                    </PopoverTrigger>
                    <PopoverSurface aria-describedby={descriptionId} role="alertdialog" style={{ padding: 20, maxWidth: 300 }}>
                        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: "4px" }}>
                            <span id={descriptionId}>{props.helpText}</span>
                            <Button onClick={() => setIsCalloutVisible(false)}>{t("labels.closeButton")}</Button>
                        </div>
                    </PopoverSurface>
                </Popover>
            </div>
        </>
    );
};

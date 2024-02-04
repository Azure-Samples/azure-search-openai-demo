import { INavLink, INavLinkGroup, INavStyles, Nav } from "@fluentui/react";

import * as React from "react";

import styles from "./NavigationPanel.module.css";

const navStyles: Partial<INavStyles> = {
    root: styles.navigationPanel,
    link: styles.navigationLink
};

export interface Link {
    name: string;
    url: string;
    icon?: string;
    key: string;
    target?: string;
}

export interface LinkGroup {
    name: string;
    links: Link[];
}

interface Props {
    title: string;
    linkGroups: LinkGroup[] | INavLinkGroup[];
    onNavLinkClicked: (link: Link) => void;
}

export const NavigationPanel = (props: Props) => {
    const _onRenderGroupHeader = (group: any): JSX.Element => {
        return <h1>{group.name}</h1>;
    };

    const onLinkClick = (ev?: React.MouseEvent<HTMLElement>, item?: INavLink) => {
        ev?.preventDefault();
        if (item && item.key) {
            props.onNavLinkClicked(item as Link);
        }
    };

    const updatedNavLinkGroups: INavLinkGroup[] = props.linkGroups.map(group => ({
        ...group,
        links: group.links.map(link => ({
            ...link,
            onClick: onLinkClick
        }))
    })) as INavLinkGroup[];

    return <Nav onRenderGroupHeader={_onRenderGroupHeader} groups={updatedNavLinkGroups} styles={navStyles} />;
};

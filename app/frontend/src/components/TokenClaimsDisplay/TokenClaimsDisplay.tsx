import { Label } from "@fluentui/react";
import { useMsal } from "@azure/msal-react";
import {
    DataGridBody,
    DataGridRow,
    DataGrid,
    DataGridHeader,
    DataGridHeaderCell,
    DataGridCell,
    createTableColumn,
    TableColumnDefinition
} from "@fluentui/react-table";
import { getTokenClaims } from "../../authConfig";
import { useState, useEffect } from "react";

type Claim = {
    name: string;
    value: string;
};

export const TokenClaimsDisplay = () => {
    const { instance } = useMsal();
    const activeAccount = instance.getActiveAccount();
    const [claims, setClaims] = useState<Record<string, unknown> | undefined>(undefined);

    useEffect(() => {
        const fetchClaims = async () => {
            setClaims(await getTokenClaims(instance));
        };

        fetchClaims();
    }, []);

    const ToString = (a: string | any) => {
        if (typeof a === "string") {
            return a;
        } else {
            return JSON.stringify(a);
        }
    };

    let createClaims = (o: Record<string, unknown> | undefined) => {
        return Object.keys(o ?? {}).map((key: string) => {
            let originalKey = key;
            try {
                // Some claim names may be a URL to a full schema, just use the last part of the URL in this case
                const url = new URL(key);
                const parts = url.pathname.split("/");
                key = parts[parts.length - 1];
            } catch (error) {
                // Do not parse key if it's not a URL
            }
            return { name: key, value: ToString((o ?? {})[originalKey]) };
        });
    };
    const items: Claim[] = createClaims(claims);

    const columns: TableColumnDefinition<Claim>[] = [
        createTableColumn<Claim>({
            columnId: "name",
            compare: (a: Claim, b: Claim) => {
                return a.name.localeCompare(b.name);
            },
            renderHeaderCell: () => {
                return "Name";
            },
            renderCell: item => {
                return item.name;
            }
        }),
        createTableColumn<Claim>({
            columnId: "value",
            compare: (a: Claim, b: Claim) => {
                return a.value.localeCompare(b.value);
            },
            renderHeaderCell: () => {
                return "Value";
            },
            renderCell: item => {
                return item.value;
            }
        })
    ];

    return (
        <div>
            <Label>ID Token Claims</Label>
            <DataGrid items={items} columns={columns} sortable getRowId={item => item.name}>
                <DataGridHeader>
                    <DataGridRow>{({ renderHeaderCell }) => <DataGridHeaderCell>{renderHeaderCell()}</DataGridHeaderCell>}</DataGridRow>
                </DataGridHeader>
                <DataGridBody<Claim>>
                    {({ item, rowId }) => <DataGridRow<Claim> key={rowId}>{({ renderCell }) => <DataGridCell>{renderCell(item)}</DataGridCell>}</DataGridRow>}
                </DataGridBody>
            </DataGrid>
        </div>
    );
};

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

type Claim = {
    name: string;
    value: string;
};

export const TokenClaimsDisplay = () => {
    const { instance } = useMsal();
    const activeAccount = instance.getActiveAccount();

    const ToString = (a: string | any) => {
        if (typeof a === "string") {
            return a;
        } else {
            return JSON.stringify(a);
        }
    };

    const items: Claim[] = activeAccount?.idTokenClaims
        ? Object.keys(activeAccount.idTokenClaims).map<Claim>((key: string) => {
              return { name: key, value: ToString((activeAccount.idTokenClaims ?? {})[key]) };
          })
        : [];

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

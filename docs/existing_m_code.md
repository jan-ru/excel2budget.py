let
    AddNullColumns = (tbl as table, names as list) as table =>
        List.Accumulate(names, tbl, (state, name) =>
            Table.AddColumn(state, name, each null, type number)),
    Source = Excel.CurrentWorkbook(){[Name="Budget"]}[Content],
    MonthMap = {"jan","feb","mrt","apr","mei","jun","jul","aug","sep","okt","nov","dec"},
    #"Renamed Months" = Table.RenameColumns(Source, List.Transform({1..12}, each {
        MonthMap{_-1} & "-26",
        "26P" & Text.PadStart(Text.From(_), 2, "0")
    })),
    #"Filtered" = Table.SelectRows(#"Renamed Months", each [Account] <> null),
    #"Unpivoted" = Table.UnpivotOtherColumns(#"Filtered", {"Entity", "Account", "DC"}, "Period", "Value"),
    #"Split Period" = Table.AddColumn(#"Unpivoted", "Jaar", each 2026, Int64.Type),
    #"Added Periode" = Table.AddColumn(#"Split Period", "Periode", each Number.From(Text.Middle([Period], 3, 2)), Int64.Type),
    #"Dropped Columns" = Table.RemoveColumns(#"Added Periode", {"Period"}),
    #"Renamed Account" = Table.RenameColumns(#"Dropped Columns", {{"Account", "Grootboekrekening"}}),
    #"Added Budgetcode" = Table.AddColumn(#"Renamed Account", "Budgetcode", each "010", type text),
    #"Added Null Columns" = AddNullColumns(#"Added Budgetcode", {"Kostenplaats", "Project"}),
    #"Added Debet" = Table.AddColumn(#"Added Null Columns", "Debet", each if [DC] = "D" then Number.Round([Value], 2) else null, type number),
    #"Added Credit" = Table.AddColumn(#"Added Debet", "Credit", each if [DC] = "C" then Number.Round(Number.Abs([Value]), 2) else null, type number),
    #"Dropped DC Value" = Table.RemoveColumns(#"Added Credit", {"DC", "Value"}),
    #"Added Hvlhd" = AddNullColumns(#"Dropped DC Value", {"Hvlhd1 Debet", "Hvlhd1 Credit", "Hvlhd2 Debet", "Hvlhd2 Credit"}),
    #"Reordered Columns" = Table.ReorderColumns(#"Added Hvlhd", {
        "Entity", "Budgetcode", "Grootboekrekening", "Kostenplaats", "Project",
        "Jaar", "Periode", "Debet", "Credit",
        "Hvlhd1 Debet", "Hvlhd1 Credit", "Hvlhd2 Debet", "Hvlhd2 Credit"
    }),
    #"Changed Type" = Table.TransformColumnTypes(#"Reordered Columns",{{"Grootboekrekening", type text}, {"Hvlhd1 Debet", type text}, {"Credit", type number}}),
    #"Rounded Off" = Table.TransformColumns(#"Changed Type",{{"Credit", each Number.Round(_, 4), type number}}),
    #"Rounded Off1" = Table.TransformColumns(#"Rounded Off",{{"Credit", each Number.Round(_, 4), type number}}),
    #"Rounded Off2" = Table.TransformColumns(#"Rounded Off1",{{"Debet", each Number.Round(_, 4), type number}})
in
    #"Rounded Off2"
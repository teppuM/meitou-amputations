# Amputations

A code and data mod for [MeitouClient](https://meitou.kenshi.wiki) 0.22.1 and newer. It adds surgery: two operating tables where your surgeon removes a squad member's limb on purpose, for instance to make room for a better prosthetic. The original Kenshi ignores it.

## What it adds

- **Operating Table**, for people. Unlocked by the research Surgery (level 4, after Medicine, costs an Ancient Science Book). Heals like a bed.
- **Skeleton Operating Bed**, for skeletons. Unlocked by the research Skeleton Operating Beds (level 4, after Skeleton Repair Beds, costs Engineering Research). Repairs faster than a Skeleton Repair Bed and, like it, needs power.
- Both are indoor furniture, built inside a building you own like any bed.

## How to operate

1. Put the patient on the table (right-click the table and use it, as with a bed).
2. Select your surgeon, right-click the patient and choose **Amputate...**, then pick Left Arm, Right Arm, Left Leg or Right Leg. A limb that is already gone is greyed out.
3. The surgeon walks over and works at the table for a few seconds under an "Amputating" progress bar. Then the limb comes off and drops to the ground, and the stump is left already tended.

The surgeon's First Aid (Robotics on a skeleton) decides how much blood (or oil) the patient loses: about a fifth of it for a master surgeon, about three fifths for a beginner. A beginner usually botches the job, which costs two and a half times as much and can knock the patient out; a second botched operation can kill. The surgeon gains skill experience from each operation, and the patient toughness, as from any lost limb.

## Install

Subscribe on the Steam Workshop, or unzip the release into Kenshi's `mods` folder and switch it on in the MeitouClient launcher. The `OperatingTables` folder holds the code (`OperatingTables.dll`), its manifest (`meitou.json`), the data (`OperatingTables.mod`) and the two tables' models.

## Building

- `OperatingTables.csproj` builds the code against an official MeitouClient release folder named by `MeitouBin` (a self-built MeitouClient is refused, since a mod compiled against it does not load in the releases): `dotnet build -c Release -p:MeitouBin=<release folder>/`.
- `data/build_data_mod.py <Kenshi data folder> <out .mod>` writes the data file from the game's own Bed and Skeleton Repair Bed; `data/description.txt` is its description.
- `models/build_tables_v2.py` builds the tables' models in Blender from the game's own furniture.

## License

GPL 3.0 or later (see `LICENSE`).

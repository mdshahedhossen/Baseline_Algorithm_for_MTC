
import csv
import os
from datetime import datetime

def save_result(result):

    file_name="ga_experiment_results.csv"

    exists=os.path.isfile(file_name)

    with open(file_name,"a",newline="") as f:

        writer=csv.writer(f)

        if not exists:

            writer.writerow([
                "DateTime",
                "Path",
                "TotalCost",
                "Distance",
                "TravelTime",
                "EnergyConsumed",
                "EnergyCharged",
                "ChargingCost",
                "FinalBattery",
                "CurrentEnergyRate",
                "ExecutionTime"
            ])

        writer.writerow([
            datetime.now(),
            result["path"],
            result["total_cost"],
            result["distance"],
            result["time"],
            result["energy_consumed"],
            result["energy_charged"],
            result["charging_cost"],
            result["final_battery"],
            result["current_energy_rate"],
            result["execution_time"]
        ])

    print("Result appended to ga_experiment_results.csv")

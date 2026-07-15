#include <limits>
#include "cadmium/simulation/root_coordinator.hpp"
#include "cadmium/simulation/logger/stdout.hpp"
#include "cadmium/simulation/logger/csv.hpp"

#include "lib/cxxopts.hpp"
#include "include/data_structures/od_datum.hpp"
#include "include/data_structures/parking_lot_schedule.hpp"
#include "include/coupled_models/carleton_university_campus.hpp"
#include "include/coupled_models/carleton_university_campus_scenario_07.hpp"
#include "include/io/load_data.hpp"

using namespace cadmium;

int main(int argc, char* argv[]) {
    // Configure options
    cxxopts::Options options("campus-evacuation", "Model and simulation of a university campus evacuation");
    options.add_options()
        ("i,parking-lot-schedules", "Parking lot schedules file name", 
          cxxopts::value<std::string>()->default_value("input_data/parking_lot_schedules/default.csv"))
        ("o,output", "Output file name", cxxopts::value<std::string>()->default_value("")) 
        ("od-data", "Origin destination data file name", 
         cxxopts::value<std::string>()->default_value("input_data/od_data/simple_poll_results.csv"))
        ("m,max-sim-time", "Max simulation time", cxxopts::value<double>()->default_value("15000.0"))
        ("scenario", "Scenario preset name (e.g. scenario_07)", cxxopts::value<std::string>()->default_value(""))
        ("h,help", "Print usage")
        ;

    // Parse options
    auto result = options.parse(argc, argv);
    if (result.count("help")) {
      std::cout << options.help() << std::endl;
      exit(0);
    }
    std::string parkingLotSchedulesFile = result["parking-lot-schedules"].as<std::string>();
    std::string outputFile = result["output"].as<std::string>();
    std::string odFile = result["od-data"].as<std::string>();
    double maxSimulationTime = result["max-sim-time"].as<double>();
    std::string scenario = result["scenario"].as<std::string>();

    if (scenario == "scenario_07") {
        parkingLotSchedulesFile = "input_data/parking_lot_schedules/scenario_07.csv";
        odFile = "input_data/od_data/scenario_07_bronson.csv";
    }

    // Load data
    std::vector<ParkingLotSchedule> schedules = loadParkingLotSchedules(parkingLotSchedulesFile);
    std::vector<ODDatum> odData = loadODData(odFile);

    // Configure model & simulator
    std::shared_ptr<Coupled> model;
    if (scenario == "scenario_07") {
        std::vector<RoutingOverride> routingOverrides =
            loadRoutingOverrides("input_data/scenarios/scenario_07_routing_overrides.csv");
        model = std::make_shared<CarletonUniversityCampusScenario07Coupled>(
            "Carleton University Campus", schedules, odData, routingOverrides);
    } else {
        model = std::make_shared<CarletonUniversityCampusCoupled>("Carleton University Campus", schedules, odData);
    }
    auto rootCoordinator = cadmium::RootCoordinator(model);
    if (outputFile.empty()) {
        rootCoordinator.setLogger<STDOUTLogger>(",");
    } else {
        rootCoordinator.setLogger<CSVLogger>(outputFile, ",");
    }

    // Run simulation
    rootCoordinator.start();
    rootCoordinator.simulate(maxSimulationTime);
    rootCoordinator.stop();	
}

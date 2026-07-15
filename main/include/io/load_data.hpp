#ifndef LOAD_DATA_HPP
#define LOAD_DATA_HPP

#include "../../lib/rapidcsv.h"
#include "../data_structures/od_datum.hpp"
#include "../data_structures/parking_lot_schedule.hpp"

#include <unordered_map>
#include <cmath>

std::vector<ODDatum> loadODData(std::string filepath) {
    rapidcsv::Document doc(filepath);
    std::vector<std::string> origins = doc.GetColumn<std::string>("ORIGIN");
    std::vector<std::string> destinations = doc.GetColumn<std::string>("DEST");
    std::vector<int> flowRates = doc.GetColumn<int>("FLOW");

    std::vector<ODDatum> odData;
    for (int i = 0; i < origins.size(); i++) {
        odData.push_back(ODDatum(origins[i], destinations[i], flowRates[i]));
    }
    return odData;
}

std::vector<ParkingLotSchedule> loadParkingLotSchedules(std::string fp) {
    rapidcsv::Document doc(fp);
    std::vector<ParkingLotSchedule> schedules;

    std::vector<std::string> ids = doc.GetColumn<std::string>("id");
    std::vector<double> e = doc.GetColumn<double>("initEventInSec");
    std::vector<double> p = doc.GetColumn<double>("periodInSec");
    std::vector<int> t = doc.GetColumn<int>("totalEvents");

    for (int i = 0; i < ids.size(); i++) {
        schedules.push_back(ParkingLotSchedule(ids[i], e[i], p[i], t[i]));
    }
    return schedules;
}

std::unordered_map<std::string, int> loadRoadLengths(std::string filepath) {
    rapidcsv::Document doc(filepath);
    std::vector<std::string> roads = doc.GetColumn<std::string>("ROAD");
    std::vector<double> lengths = doc.GetColumn<double>("LENGTH_M");

    std::unordered_map<std::string, int> out;
    for (int i = 0; i < (int)roads.size(); i++) {
        out[roads[i]] = (int)std::lround(lengths[i]);
    }
    return out;
}

std::unordered_map<std::string, int> loadRoadSpeeds(std::string filepath) {
    rapidcsv::Document doc(filepath);
    std::vector<std::string> roads = doc.GetColumn<std::string>("ROAD");
    std::vector<double> speeds = doc.GetColumn<double>("SPEED_KPH");

    std::unordered_map<std::string, int> out;
    for (int i = 0; i < (int)roads.size(); i++) {
        out[roads[i]] = (int)std::lround(speeds[i]); // store as int kph
    }
    return out;
}

#include "../data_structures/routing_override.hpp"

std::vector<RoutingOverride> loadRoutingOverrides(std::string filepath) {
    rapidcsv::Document doc(filepath);
    std::vector<std::string> intersections = doc.GetColumn<std::string>("intersection");
    std::vector<std::string> srcs = doc.GetColumn<std::string>("src");
    std::vector<std::string> dests = doc.GetColumn<std::string>("dest");

    std::vector<RoutingOverride> overrides;
    for (int i = 0; i < (int)intersections.size(); i++) {
        RoutingOverride override;
        override.intersection = intersections[i];
        override.src = srcs[i];
        override.dest = dests[i];
        overrides.push_back(override);
    }
    return overrides;
}

#endif // LOAD_DATA_HPP

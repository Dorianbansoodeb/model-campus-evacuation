#ifndef CARLETON_UNIVERSITY_CAMPUS_SCENARIO_09_HPP
#define CARLETON_UNIVERSITY_CAMPUS_SCENARIO_09_HPP

#include <vector>
#include <map>
#include <set>
#include <string>
#include "cadmium/modeling/devs/coupled.hpp"
#include "../atomic_models/parking_lot.hpp"
#include "../atomic_models/road.hpp"
#include "../atomic_models/intersection.hpp"
#include "../atomic_models/intersection_with_overrides.hpp"
#include "../data_structures/od_datum.hpp"
#include "../data_structures/parking_lot_schedule.hpp"
#include "../data_structures/routing_override.hpp"
#include "../io/load_data.hpp"

using namespace cadmium;

// Scenario 09: Scenario 08 topology (Bronson UD / r24 blocked; Stadium Way open)
// plus Scenario 07 emergency (r28 Raven→Bronson + IntersectionWithOverrides at Raven).
// P1/P2 → Colonel By; P3–P7 → NE / Stadium; P3/P4 prefer Raven emergency (OD + overrides).
struct CarletonUniversityCampusScenario09Coupled : public Coupled {

    CarletonUniversityCampusScenario09Coupled(const std::string& id, std::vector<ParkingLotSchedule> parkingLotSchedules,
                                    const std::vector<ODDatum>& odData,
                                    const std::vector<RoutingOverride>& routingOverrides): Coupled(id) {
        // Road names, as per documentation in the final report.
        std::string r01Name = "Library Rd & P1 to Library Rd & University Dr";
        std::string r02Name = "Library Rd & P1 to Campus Ave & Library Rd";
        std::string r03Name = "Library Rd & University Dr to Library Rd & P1";
        std::string r04Name = "Campus Ave & Library Rd to Library Rd & P1";
        std::string r05Name = "Campus Ave & Library Rd to Campus Ave & P2";
        std::string r06Name = "Campus Ave & P2 to Campus Ave & University Dr";
        std::string r07Name = "Campus Ave & University Dr to Library Rd & University Dr";
        std::string r08Name = "Library Rd & University Dr to Campus Ave & University Dr";
        std::string r09Name = "Campus Ave & University Dr to Raven Rd & University Dr";
        std::string r10Name = "Raven Rd & University Dr to Campus Ave & University Dr";
        std::string r11Name = "Raven Rd & University Dr to P3 & Raven Rd";
        std::string r12Name = "P3 & Raven Rd to Raven Rd & University Dr";
        std::string r13Name = "P3 & Raven Rd to Bronson Ave & Raven Rd";
        std::string r14Name = "Library Rd & University Dr to Colonel By Dr & University Dr";
        std::string r15Name = "Raven Rd & University Dr to P4 & University Dr";
        std::string r16Name = "P4 & University Dr to Raven Rd & University Dr";
        std::string r17Name = "P4 & University Dr to Stadium Way & University Dr";
        std::string r18Name = "Stadium Way & University Dr to P4 & University Dr";
        std::string r19Name = "Stadium Way & University Dr to P5 & Stadium Way";
        std::string r20Name = "P5 & Stadium Way to Stadium Way & University Dr";
        std::string r21Name = "P5 & Stadium Way to Bronson Ave & Stadium Way";
        std::string r22Name = "Stadium Way & University Dr to Roundabout";
        std::string r23Name = "Roundabout to Stadium Way & University Dr";
        // r24 blocked: Roundabout to Bronson Ave & University Dr (main UD exit closed)
        std::string r25Name = "Roundabout to Campus Ave & P6";
        std::string r26Name = "Campus Ave & P6 to Roundabout";
        std::string r27Name = "Campus Ave & P6 to Campus Ave & Library Rd";
        std::string r28Name = "Raven Rd & University Dr to Bronson Ave & Raven Rd";

        // Out roads
        std::vector<std::string> x01OutRoads = {r01Name, r02Name};
        std::vector<std::string> x02OutRoads = {r03Name, r08Name, r14Name};
        std::vector<std::string> x03OutRoads = {r04Name, r05Name};
        std::vector<std::string> x04OutRoads = {r06Name};
        std::vector<std::string> x05OutRoads = {r07Name, r09Name};
        std::vector<std::string> x06OutRoads = {r10Name, r11Name, r15Name, r28Name};
        std::vector<std::string> x07OutRoads = {r12Name, r13Name};
        std::vector<std::string> x08OutRoads = {};
        std::vector<std::string> x09OutRoads = {};
        std::vector<std::string> x10OutRoads = {r16Name, r17Name};
        std::vector<std::string> x11OutRoads = {r18Name, r19Name, r22Name};
        std::vector<std::string> x12OutRoads = {r20Name, r21Name};
        std::vector<std::string> x13OutRoads = {};
        // Roundabout: Stadium Way + Campus Ave only (no Bronson UD)
        std::vector<std::string> x14OutRoads = {r23Name, r25Name};
        std::vector<std::string> x15OutRoads = {};
        std::vector<std::string> x16OutRoads = {r26Name, r27Name};

        // Create models
        auto p1 = addComponent<ParkingLot>("P1", parkingLotSchedules);
        auto p2 = addComponent<ParkingLot>("P2", parkingLotSchedules);
        auto p3 = addComponent<ParkingLot>("P3", parkingLotSchedules);
        auto p4 = addComponent<ParkingLot>("P4", parkingLotSchedules);
        auto p5 = addComponent<ParkingLot>("P5", parkingLotSchedules);
        auto p6 = addComponent<ParkingLot>("P6", parkingLotSchedules);
        auto p7 = addComponent<ParkingLot>("P7", parkingLotSchedules);
        auto x01 = addComponent<Intersection>("Library Rd & P1", odData, x01OutRoads);
        auto x02 = addComponent<Intersection>("Library Rd & University Dr", odData, x02OutRoads);
        auto x03 = addComponent<Intersection>("Campus Ave & Library Rd", odData, x03OutRoads);
        auto x04 = addComponent<Intersection>("Campus Ave & P2", odData, x04OutRoads);
        auto x05 = addComponent<Intersection>("Campus Ave & University Dr", odData, x05OutRoads);
        auto x06 = addComponent<IntersectionWithOverrides>("Raven Rd & University Dr", odData, x06OutRoads, routingOverrides);
        auto x07 = addComponent<Intersection>("P3 & Raven Rd", odData, x07OutRoads);
        auto x08 = addComponent<Intersection>("Bronson Ave & Raven Rd", odData, x08OutRoads);
        auto x09 = addComponent<Intersection>("Colonel By Dr & University Dr", odData, x09OutRoads);
        auto x10 = addComponent<Intersection>("P4 & University Dr", odData, x10OutRoads);
        auto x11 = addComponent<Intersection>("Stadium Way & University Dr", odData, x11OutRoads);
        auto x12 = addComponent<Intersection>("P5 & Stadium Way", odData, x12OutRoads);
        auto x13 = addComponent<Intersection>("Bronson Ave & Stadium Way", odData, x13OutRoads);
        auto x14 = addComponent<Intersection>("Roundabout", odData, x14OutRoads);
        auto x15 = addComponent<Intersection>("Bronson Ave & University Dr", odData, x15OutRoads);
        auto x16 = addComponent<Intersection>("Campus Ave & P6", odData, x16OutRoads);

        //road components
        auto roadLengths = loadRoadLengths("data_creation/sim_road_lengths.csv");
        auto roadSpeeds  = loadRoadSpeeds("data_creation/sim_road_lengths.csv");
        auto r01 = addComponent<Road>(r01Name, roadLengths.at(r01Name), roadSpeeds.at(r01Name));
        auto r02 = addComponent<Road>(r02Name, roadLengths.at(r02Name), roadSpeeds.at(r02Name));
        auto r03 = addComponent<Road>(r03Name, roadLengths.at(r03Name), roadSpeeds.at(r03Name));
        auto r04 = addComponent<Road>(r04Name, roadLengths.at(r04Name), roadSpeeds.at(r04Name));
        auto r05 = addComponent<Road>(r05Name, roadLengths.at(r05Name), roadSpeeds.at(r05Name));
        auto r06 = addComponent<Road>(r06Name, roadLengths.at(r06Name), roadSpeeds.at(r06Name));
        auto r07 = addComponent<Road>(r07Name, roadLengths.at(r07Name), roadSpeeds.at(r07Name));
        auto r08 = addComponent<Road>(r08Name, roadLengths.at(r08Name), roadSpeeds.at(r08Name));
        auto r09 = addComponent<Road>(r09Name, roadLengths.at(r09Name), roadSpeeds.at(r09Name));
        auto r10 = addComponent<Road>(r10Name, roadLengths.at(r10Name), roadSpeeds.at(r10Name));
        auto r11 = addComponent<Road>(r11Name, roadLengths.at(r11Name), roadSpeeds.at(r11Name));
        auto r12 = addComponent<Road>(r12Name, roadLengths.at(r12Name), roadSpeeds.at(r12Name));
        auto r13 = addComponent<Road>(r13Name, roadLengths.at(r13Name), roadSpeeds.at(r13Name));
        auto r14 = addComponent<Road>(r14Name, roadLengths.at(r14Name), roadSpeeds.at(r14Name));
        auto r15 = addComponent<Road>(r15Name, roadLengths.at(r15Name), roadSpeeds.at(r15Name));
        auto r16 = addComponent<Road>(r16Name, roadLengths.at(r16Name), roadSpeeds.at(r16Name));
        auto r17 = addComponent<Road>(r17Name, roadLengths.at(r17Name), roadSpeeds.at(r17Name));
        auto r18 = addComponent<Road>(r18Name, roadLengths.at(r18Name), roadSpeeds.at(r18Name));
        auto r19 = addComponent<Road>(r19Name, roadLengths.at(r19Name), roadSpeeds.at(r19Name));
        auto r20 = addComponent<Road>(r20Name, roadLengths.at(r20Name), roadSpeeds.at(r20Name));
        auto r21 = addComponent<Road>(r21Name, roadLengths.at(r21Name), roadSpeeds.at(r21Name));
        auto r22 = addComponent<Road>(r22Name, roadLengths.at(r22Name), roadSpeeds.at(r22Name));
        auto r23 = addComponent<Road>(r23Name, roadLengths.at(r23Name), roadSpeeds.at(r23Name));
        auto r25 = addComponent<Road>(r25Name, roadLengths.at(r25Name), roadSpeeds.at(r25Name));
        auto r26 = addComponent<Road>(r26Name, roadLengths.at(r26Name), roadSpeeds.at(r26Name));
        auto r27 = addComponent<Road>(r27Name, roadLengths.at(r27Name), roadSpeeds.at(r27Name));
        auto r28 = addComponent<Road>(r28Name, roadLengths.at(r28Name), roadSpeeds.at(r28Name));



        // Couple intersection inputs
        addCoupling(p1->exit, x01->in);
        addCoupling(r03->exit, x01->in);
        addCoupling(r04->exit, x01->in);
        addCoupling(r01->exit, x02->in);
        addCoupling(r07->exit, x02->in);
        addCoupling(r02->exit, x03->in);
        addCoupling(r27->exit, x03->in);
        addCoupling(p2->exit, x04->in);
        addCoupling(r05->exit, x04->in);
        addCoupling(r06->exit, x05->in);
        addCoupling(r08->exit, x05->in);
        addCoupling(r10->exit, x05->in);
        addCoupling(r09->exit, x06->in);
        addCoupling(r12->exit, x06->in);
        addCoupling(r16->exit, x06->in);
        addCoupling(p3->exit, x07->in);
        addCoupling(r11->exit, x07->in);
        addCoupling(r13->exit, x08->in);
        addCoupling(r28->exit, x08->in);
        addCoupling(r14->exit, x09->in);
        addCoupling(p4->exit, x10->in);
        addCoupling(r15->exit, x10->in);
        addCoupling(r18->exit, x10->in);
        addCoupling(r17->exit, x11->in);
        addCoupling(r20->exit, x11->in);
        addCoupling(r23->exit, x11->in);
        addCoupling(p5->exit, x12->in);
        addCoupling(r19->exit, x12->in);
        addCoupling(r21->exit, x13->in);
        addCoupling(p7->exit, x14->in);
        addCoupling(r22->exit, x14->in);
        addCoupling(r26->exit, x14->in);
        addCoupling(p6->exit, x16->in);
        addCoupling(r25->exit, x16->in);

        // Couple intersection outputs
        addCoupling(x01->out1, r01->entrance);
        addCoupling(x01->out2, r02->entrance);
        addCoupling(x02->out1, r03->entrance);
        addCoupling(x02->out2, r08->entrance);
        addCoupling(x02->out3, r14->entrance);
        addCoupling(x03->out1, r04->entrance);
        addCoupling(x03->out2, r05->entrance);
        addCoupling(x04->out1, r06->entrance);
        addCoupling(x05->out1, r07->entrance);
        addCoupling(x05->out2, r09->entrance);
        addCoupling(x06->out1, r10->entrance);
        addCoupling(x06->out2, r11->entrance);
        addCoupling(x06->out3, r15->entrance);
        addCoupling(x06->out4, r28->entrance);
        addCoupling(x07->out1, r12->entrance);
        addCoupling(x07->out2, r13->entrance);
        addCoupling(x10->out1, r16->entrance);
        addCoupling(x10->out2, r17->entrance);
        addCoupling(x11->out1, r18->entrance);
        addCoupling(x11->out2, r19->entrance);
        addCoupling(x11->out3, r22->entrance);
        addCoupling(x12->out1, r20->entrance);
        addCoupling(x12->out2, r21->entrance);
        addCoupling(x14->out1, r23->entrance);
        addCoupling(x14->out2, r25->entrance);
        addCoupling(x16->out1, r26->entrance);
        addCoupling(x16->out2, r27->entrance);
    }
};
#endif // CARLETON_UNIVERSITY_CAMPUS_SCENARIO_09_HPP

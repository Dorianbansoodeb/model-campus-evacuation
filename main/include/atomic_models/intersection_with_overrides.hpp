#ifndef INTERSECTION_WITH_OVERRIDES_HPP
#define INTERSECTION_WITH_OVERRIDES_HPP

#include <iostream>
#include <vector>
#include <string>
#include <cassert>
#include "cadmium/modeling/devs/atomic.hpp"
#include "../data_structures/od_datum.hpp"
#include "../data_structures/routing_override.hpp"
#include "../data_structures/vehicle.hpp"
#include "../constants.hpp"

using namespace cadmium;

struct IntersectionWithOverridesState {
    std::vector<ODDatum> odData;
    std::vector<Vehicle> vehicles;
    std::vector<std::string> outRoads;
    std::vector<RoutingOverride> routingOverrides;

    explicit IntersectionWithOverridesState() {}
};

#ifndef NO_LOGGING
std::ostream& operator<<(std::ostream &out, const IntersectionWithOverridesState& state) {
    return out << "Number of vehicles in intersection: " << state.vehicles.size();
}
#endif

// Scenario 07 only: same OD routing as Intersection, plus per-lot overrides at this node.
class IntersectionWithOverrides : public Atomic<IntersectionWithOverridesState> {
public:
    Port<Vehicle> in;
    Port<Vehicle> out1;
    Port<Vehicle> out2;
    Port<Vehicle> out3;
    Port<Vehicle> out4;

    IntersectionWithOverrides(const std::string id, const std::vector<ODDatum>& odData,
                              const std::vector<std::string>& outRoads,
                              const std::vector<RoutingOverride>& routingOverrides):
                              Atomic<IntersectionWithOverridesState>(id, IntersectionWithOverridesState()) {
        in = addInPort<Vehicle>("in");
        out1 = addOutPort<Vehicle>("out1");
        out2 = addOutPort<Vehicle>("out2");
        out3 = addOutPort<Vehicle>("out3");
        out4 = addOutPort<Vehicle>("out4");

        for (int i = 0; i < odData.size(); i++) {
            if (odData[i].origin == id and odData[i].flowRate != 0) {
                state.odData.push_back(odData[i]);
            }
        }
        assert(outRoads.size() <= 4);
        state.outRoads = outRoads;

        for (const RoutingOverride& override : routingOverrides) {
            if (override.intersection == id) {
                state.routingOverrides.push_back(override);
            }
        }
    }

    void internalTransition(IntersectionWithOverridesState& state) const override {
        state.vehicles.clear();
    }

    void externalTransition(IntersectionWithOverridesState& state, double e) const override {
        if (!in->getBag().empty()) {
            for (Vehicle v : in->getBag()) {
                v.dest = selectDest(state, v);
                state.vehicles.push_back(v);
            }
        }
    }

    void output(const IntersectionWithOverridesState& state) const override {
        for (Vehicle v : state.vehicles) {
            int o = getOutputPortID(v, state.outRoads);
            if (o == 1) {
                out1->addMessage(v);
            } else if (o == 2) {
                out2->addMessage(v);
            } else if (o == 3) {
                out3->addMessage(v);
            } else if (o == 4) {
                out4->addMessage(v);
            }
        }
    }

    [[nodiscard]] double timeAdvance(const IntersectionWithOverridesState& state) const override {
        if (!state.vehicles.empty()) {
            return 0.0;
        }
        return infinity;
    }

private:
    std::string selectDest(const IntersectionWithOverridesState& state, const Vehicle& vehicle) const {
        for (const RoutingOverride& override : state.routingOverrides) {
            if (override.src == vehicle.src) {
                return override.dest;
            }
        }

        std::string dest = "";
        if (state.odData.empty()) {
            return dest;
        }
        if (state.odData.size() == 1) {
            return state.odData.front().dest;
        }

        std::vector<ODDatum> data = state.odData;
        for (int i = 1; i < data.size(); i++) {
            assert((data[i].flowRate != 0) && "Assume OD data does not have flow rates equal to zero");
            data[i].flowRate = data[i - 1].flowRate + data[i].flowRate;
        }

        int r = std::rand() % data.back().flowRate + 1;
        int i = 0;
        while (dest.empty() and i < data.size()) {
            if (r <= data[i].flowRate) {
                dest = data[i].dest;
            }
            i++;
        }
        assert(!dest.empty());
        return dest;
    }

    int getOutputPortID(const Vehicle v, const std::vector<std::string>& outRoads) const {
        std::string target = v.dest;
        int counter = 0;
        int id = counter;

        for (std::string r : outRoads) {
            counter++;
            if (target.compare(r) == 0) {
                id = counter;
            }
        }
        return id;
    }
};

#endif  // INTERSECTION_WITH_OVERRIDES_HPP

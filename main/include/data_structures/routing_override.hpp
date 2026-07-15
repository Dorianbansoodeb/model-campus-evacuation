#ifndef ROUTING_OVERRIDE_HPP
#define ROUTING_OVERRIDE_HPP

#include <string>

struct RoutingOverride {
    std::string intersection;
    std::string src;
    std::string dest;
};

#endif  // ROUTING_OVERRIDE_HPP

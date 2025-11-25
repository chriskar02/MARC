"""Network adapter discovery and configuration for robot connections."""

import socket
import ipaddress
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class NetworkAdapter:
    """Represents a network adapter configuration."""
    name: str
    ip_address: str
    netmask: str
    gateway: str
    meca_address: str  # Calculated Meca500 address for this subnet

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "ip_address": self.ip_address,
            "netmask": self.netmask,
            "gateway": self.gateway,
            "meca_address": self.meca_address,
        }


def get_ipv4_adapters() -> List[NetworkAdapter]:
    """
    Discover all active IPv4 network adapters and calculate Meca500 addresses.
    
    Returns:
        List of NetworkAdapter objects with calculated Meca addresses
    """
    adapters = []
    
    try:
        # Get all network interfaces
        hostname = socket.gethostname()
        
        # Use socket.getaddrinfo to find local addresses
        for info in socket.getaddrinfo(hostname, None):
            if info[0] != socket.AF_INET:
                continue
            
            ip = info[4][0]
            
            # Skip loopback
            if ip.startswith("127."):
                continue
            
            # Try to get netmask for this IP
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect((ip, 80))
                local_ip = s.getsockname()[0]
                s.close()
                
                # Calculate netmask and gateway
                netmask = "255.255.255.0"  # Default /24
                gateway = _calculate_gateway(local_ip, netmask)
                meca_addr = _calculate_meca_address(local_ip, netmask)
                
                adapter = NetworkAdapter(
                    name=f"Adapter - {local_ip}",
                    ip_address=local_ip,
                    netmask=netmask,
                    gateway=gateway,
                    meca_address=meca_addr,
                )
                adapters.append(adapter)
                
            except Exception as e:
                logger.debug(f"Error getting netmask for {ip}: {e}")
                continue
        
        # If no adapters found via getaddrinfo, try alternative method
        if not adapters:
            adapters = _get_adapters_windows()
    
    except Exception as e:
        logger.error("Error discovering network adapters", error=str(e))
    
    return adapters


def _get_adapters_windows() -> List[NetworkAdapter]:
    """Fallback: Get adapters on Windows using socket operations."""
    adapters = []
    
    try:
        # Get local hostname and its IPs
        hostname = socket.gethostname()
        ips = socket.gethostbyname_ex(hostname)
        
        for ip in ips[2]:
            if ip.startswith("127."):
                continue
            
            netmask = "255.255.255.0"
            gateway = _calculate_gateway(ip, netmask)
            meca_addr = _calculate_meca_address(ip, netmask)
            
            adapter = NetworkAdapter(
                name=f"Adapter - {ip}",
                ip_address=ip,
                netmask=netmask,
                gateway=gateway,
                meca_address=meca_addr,
            )
            adapters.append(adapter)
    
    except Exception as e:
        logger.error("Error discovering Windows adapters", error=str(e))
    
    return adapters


def _calculate_gateway(ip: str, netmask: str) -> str:
    """Calculate gateway address from IP and netmask (usually .1)."""
    try:
        network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
        # Gateway is typically the first usable address in the subnet
        return str(network.network_address + 1)
    except Exception as e:
        logger.warning(f"Error calculating gateway: {e}")
        return "192.168.0.1"  # Fallback


def _calculate_meca_address(ip: str, netmask: str) -> str:
    """
    Calculate recommended Meca500 address based on local IP and subnet.
    
    For a /24 subnet, uses .100 as default Meca500 address.
    For other subnets, uses a reasonable address in the subnet.
    """
    try:
        network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
        
        # For /24 networks, default to .100
        if network.prefixlen == 24:
            return str(ipaddress.IPv4Address(network.network_address) + 100)
        
        # For other networks, use a reasonable address
        # Use 3/4 of the way through the subnet
        usable_hosts = list(network.hosts())
        if usable_hosts:
            idx = max(0, len(usable_hosts) - 50)
            return str(usable_hosts[idx])
        
        # Fallback
        return str(network.network_address + 100)
    
    except Exception as e:
        logger.warning(f"Error calculating Meca address: {e}")
        return "192.168.0.100"  # Fallback


def validate_meca_address(address: str, ip: str, netmask: str) -> bool:
    """
    Validate that a Meca address is on the same subnet as the given IP.
    
    Args:
        address: IP address to validate
        ip: Local IP address
        netmask: Netmask for the subnet
    
    Returns:
        True if address is on the same subnet as ip/netmask
    """
    try:
        network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
        meca_ip = ipaddress.IPv4Address(address)
        return meca_ip in network
    except Exception as e:
        logger.error(f"Error validating address: {e}")
        return False

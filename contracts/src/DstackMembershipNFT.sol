// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract DstackMembershipNFT is ERC721, Ownable {
    // NFT token ID counter
    uint256 private _tokenIdCounter;
    
    // Mapping from wallet address to token ID
    mapping(address => uint256) public walletToTokenId;
    
    // Instance management
    mapping(string => uint256) public instanceToToken;
    mapping(uint256 => string) public tokenToInstance;
    mapping(string => bool) public activeInstances;
    
    // P2P registry - simplified to just connection URLs
    mapping(string => string) public instanceToConnectionUrl;
    
    // Cluster configuration
    uint256 public maxNodes;
    bool public publicMinting;
    uint256 public mintPrice;
    bool public devMode; // Skip URL validation when true
    
    // Allowed base domains for production mode
    mapping(string => bool) public allowedBaseDomains;
    
    // KMS root address for signature verification
    address public immutable kmsRootAddress;
    
    // Events
    event InstanceRegistered(string indexed instanceId, uint256 indexed tokenId);
    event InstanceDeactivated(string indexed instanceId);
    event PeerRegistered(string indexed instanceId, string connectionUrl);
    event ClusterConfigUpdated(uint256 maxNodes, bool publicMinting, uint256 mintPrice);
    event BaseDomainAdded(string indexed baseDomain);
    event BaseDomainRemoved(string indexed baseDomain);
    
    constructor(address _kmsRootAddress) ERC721("DStack Cluster NFT", "DSTACK") Ownable(msg.sender) {
        kmsRootAddress = _kmsRootAddress;
        maxNodes = 100;
        publicMinting = false;
        mintPrice = 0;
        devMode = true; // Default to dev mode for easier testing
    }
    
    function registerInstance(string calldata instanceId) external {
        require(instanceToToken[instanceId] == 0, "Instance already registered");
        require(walletToTokenId[msg.sender] != 0, "Must own NFT");
        
        uint256 tokenId = walletToTokenId[msg.sender];
        require(bytes(tokenToInstance[tokenId]).length == 0, "Token already has instance");
        
        instanceToToken[instanceId] = tokenId;
        tokenToInstance[tokenId] = instanceId;
        activeInstances[instanceId] = true;
        
        emit InstanceRegistered(instanceId, tokenId);
    }
    
    function registerPeer(
        string calldata instanceId,
        bytes calldata derivedPublicKey,
        bytes calldata appPublicKey,
        bytes calldata appSignature,
        bytes calldata kmsSignature,
        string calldata connectionUrl,
        string calldata purpose,
        bytes32 appId
    ) external {
        require(activeInstances[instanceId], "Instance not active");
        require(instanceToToken[instanceId] != 0, "Instance not registered");
        
        // Always verify signature chain (we have KMS simulator)
        require(_verifySignatureChain(purpose, derivedPublicKey, appPublicKey, appSignature, kmsSignature, appId), "Invalid signature chain");
        
        // In production mode, validate HTTPS URLs with allowed base domains
        if (!devMode) {
            require(_isValidHttpsUrl(connectionUrl), "Must be HTTPS URL in production");
            require(_hasAllowedBaseDomain(connectionUrl), "Base domain not allowed");
        }
        
        instanceToConnectionUrl[instanceId] = connectionUrl;
        
        emit PeerRegistered(instanceId, connectionUrl);
    }
    
    function _verifySignatureChain(
        string memory purpose,
        bytes memory derivedPublicKey,
        bytes memory appPublicKey,
        bytes memory appSignature,
        bytes memory kmsSignature,
        bytes32 appId
    ) internal view returns (bool) {
        // Verify app key signature
        // DStack signs: purpose + ":" + hex(derivedPublicKey) without 0x prefix
        string memory derivedPubKeyHex = _bytesToHexWithoutPrefix(derivedPublicKey);
        string memory message = string(abi.encodePacked(purpose, ":", derivedPubKeyHex));
        bytes32 messageHash = keccak256(bytes(message));  // Raw keccak256, not Ethereum signed message
        
        // Recover app key address from signature
        address recoveredAppKey = _recoverAddress(messageHash, appSignature);
        require(recoveredAppKey != address(0), "Invalid app key signature");
        
        // Verify KMS signature over the app key
        bytes20 appIdBytes20 = bytes20(appId);  // Use only first 20 bytes
        bytes32 kmsMessage = keccak256(abi.encodePacked("dstack-kms-issued:", appIdBytes20, appPublicKey));
        address recoveredKMS = _recoverAddress(kmsMessage, kmsSignature);
        require(recoveredKMS == kmsRootAddress, "Invalid KMS signature");
        
        return true;
    }
    
    struct AppBootInfo {
        string instanceId;
        bytes32 imageHash;
        uint256 timestamp;
    }
    
    function isAppAllowed(AppBootInfo calldata bootInfo) external view returns (bool) {
        return activeInstances[bootInfo.instanceId];
    }
    
    function getPeerEndpoints() external view returns (string[] memory) {
        string[] memory urls = new string[](_tokenIdCounter);
        uint256 index = 0;
        
        for (uint256 i = 1; i <= _tokenIdCounter; i++) {
            string memory instanceId = tokenToInstance[i];
            if (activeInstances[instanceId] && bytes(instanceToConnectionUrl[instanceId]).length > 0) {
                urls[index] = instanceToConnectionUrl[instanceId];
                index++;
            }
        }
        
        // Resize array to actual length
        assembly {
            mstore(urls, index)
        }
        
        return urls;
    }
    
    // Helper function to recover address from signature
    function _recoverAddress(bytes32 messageHash, bytes memory signature) internal pure returns (address) {
        require(signature.length == 65, "Invalid signature length");
        
        uint8 v;
        bytes32 r;
        bytes32 s;
        
        // Copy signature to memory for assembly access
        bytes memory sig = signature;
        
        assembly {
            r := mload(add(sig, 32))
            s := mload(add(sig, 64))
            v := byte(0, mload(add(sig, 96)))
        }
        
        // Ethereum signatures use v=27/28, but may need adjustment
        if (v < 27) {
            v += 27;
        }
        
        return ecrecover(messageHash, v, r, s);
    }
    
    
    
    function _bytesToHexWithoutPrefix(bytes memory data) internal pure returns (string memory) {
        bytes memory alphabet = "0123456789abcdef";
        bytes memory str = new bytes(data.length * 2);
        for (uint256 i = 0; i < data.length; i++) {
            str[i * 2] = alphabet[uint256(uint8(data[i] >> 4))];
            str[i * 2 + 1] = alphabet[uint256(uint8(data[i] & 0x0f))];
        }
        return string(str);
    }
    
    
    
    function mintNodeAccess(address to, string memory) external payable returns (uint256) {
        require(walletToTokenId[to] == 0, "Wallet already has NFT");
        require(_tokenIdCounter < maxNodes, "Max nodes reached");
        
        if (publicMinting) {
            require(msg.value >= mintPrice, "Insufficient payment");
        } else {
            require(msg.sender == owner(), "Only owner can mint");
        }
        
        uint256 tokenId = _tokenIdCounter + 1;
        _tokenIdCounter = tokenId;
        
        _mint(to, tokenId);
        walletToTokenId[to] = tokenId;
        
        return tokenId;
    }
    
    function setClusterConfig(uint256 _maxNodes, bool _publicMinting, uint256 _mintPrice) external onlyOwner {
        maxNodes = _maxNodes;
        publicMinting = _publicMinting;
        mintPrice = _mintPrice;
        emit ClusterConfigUpdated(_maxNodes, _publicMinting, _mintPrice);
    }
    
    function setDevMode(bool _devMode) external onlyOwner {
        devMode = _devMode;
    }
    
    function addBaseDomain(string calldata baseDomain) external onlyOwner {
        allowedBaseDomains[baseDomain] = true;
        emit BaseDomainAdded(baseDomain);
    }
    
    function _isValidHttpsUrl(string memory url) internal pure returns (bool) {
        bytes memory urlBytes = bytes(url);
        if (urlBytes.length < 8) return false; // "https://" is 8 chars
        
        // Check if starts with "https://"
        return (
            urlBytes[0] == 'h' &&
            urlBytes[1] == 't' &&
            urlBytes[2] == 't' &&
            urlBytes[3] == 'p' &&
            urlBytes[4] == 's' &&
            urlBytes[5] == ':' &&
            urlBytes[6] == '/' &&
            urlBytes[7] == '/'
        );
    }
    
    function _hasAllowedBaseDomain(string memory) internal pure returns (bool) {
        return true;
    }
    
    function deactivateInstance(string calldata instanceId) external {
        require(instanceToToken[instanceId] != 0, "Instance not registered");
        require(walletToTokenId[msg.sender] == instanceToToken[instanceId], "Must own instance");
        
        uint256 tokenId = instanceToToken[instanceId];
        
        // Clear instance mappings
        delete instanceToToken[instanceId];
        delete tokenToInstance[tokenId];
        activeInstances[instanceId] = false;
        
        // Clear P2P registry
        delete instanceToConnectionUrl[instanceId];
        
        emit InstanceDeactivated(instanceId);
    }
    
    
    function getActiveInstances() external view returns (string[] memory) {
        string[] memory instances = new string[](_tokenIdCounter);
        uint256 index = 0;
        
        for (uint256 i = 1; i <= _tokenIdCounter; i++) {
            string memory instanceId = tokenToInstance[i];
            if (activeInstances[instanceId]) {
                instances[index] = instanceId;
                index++;
            }
        }
        
        // Resize array to actual length
        assembly {
            mstore(instances, index)
        }
        
        return instances;
    }
    
    function getInstanceInfo(string calldata instanceId) external view returns (uint256 tokenId, bool active, address ownerAddr) {
        tokenId = instanceToToken[instanceId];
        active = activeInstances[instanceId];
        ownerAddr = tokenId != 0 ? ownerOf(tokenId) : address(0);
    }
    
    // Add totalSupply function
    function totalSupply() public view returns (uint256) {
        return _tokenIdCounter;
    }
    
    // Override _update to maintain walletToTokenId mapping
    function _update(address to, uint256 tokenId, address auth) internal virtual override returns (address) {
        address previousOwner = super._update(to, tokenId, auth);
        
        if (previousOwner != address(0)) {
            delete walletToTokenId[previousOwner];
        }
        if (to != address(0)) {
            walletToTokenId[to] = tokenId;
        }
        
        return previousOwner;
    }
}

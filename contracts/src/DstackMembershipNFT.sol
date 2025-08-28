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
    
    // Leader election state
    address public currentLeader;
    uint256 public currentLeaderTokenId;
    uint256 public totalActiveNodes;
    uint256 public requiredVotes;
    
    // Voting state
    mapping(address => uint256) public noConfidenceCount;
    mapping(address => Vote) public currentVotes;
    
    // Counter attestations (TEE-authenticated)
    mapping(string => uint256) public latestCounterValue;   // instanceId → counter value
    mapping(string => uint256) public lastAttestationTime; // instanceId → timestamp
    
    // Vote struct
    struct Vote {
        address voter;
        address target;
        uint256 tokenId;
        bool isNoConfidence;
        uint256 timestamp;
    }
    
    // KMS root address for signature verification
    address public immutable kmsRootAddress;
    
    // Events
    event LeaderElected(address indexed leader, uint256 indexed tokenId, string indexed instanceId);
    event VoteCast(address indexed voter, address indexed target, bool isNoConfidence);
    event LeaderChallenged(address indexed newLeader, address indexed oldLeader, uint256 voteCount);
    event InstanceRegistered(string indexed instanceId, uint256 indexed tokenId);
    event InstanceDeactivated(string indexed instanceId);
    event CounterAttestation(string indexed instanceId, uint256 value, uint256 timestamp);
    
    constructor(address _kmsRootAddress) ERC721("DStack Membership NFT", "DSTACK") Ownable(msg.sender) {
        kmsRootAddress = _kmsRootAddress;
    }
    
    // Register instance (single step)
    function registerInstance(string calldata instanceId) external {
        require(instanceToToken[instanceId] == 0, "Instance already registered");
        require(walletToTokenId[msg.sender] != 0, "Must own NFT");
        
        uint256 tokenId = walletToTokenId[msg.sender];
        require(bytes(tokenToInstance[tokenId]).length == 0, "Token already has instance");
        
        instanceToToken[instanceId] = tokenId;
        tokenToInstance[tokenId] = instanceId;
        activeInstances[instanceId] = true;
        totalActiveNodes++;
        
        // Update required votes for Byzantine fault tolerance
        requiredVotes = (totalActiveNodes / 2) + 1;
        
        emit InstanceRegistered(instanceId, tokenId);
    }
    
    // Submit counter attestation with TEE authentication
    function submitCounterAttestation(
        string calldata instanceId, 
        uint256 value, 
        bytes calldata appKeySignature,
        bytes calldata kmsSignature
    ) external {
        require(activeInstances[instanceId], "Instance not active");
        
        // Verify signature chain: app key -> KMS root
        require(_verifySignatureChain(instanceId, value, appKeySignature, kmsSignature), "Invalid signature chain");
        
        // Update counter state
        latestCounterValue[instanceId] = value;
        lastAttestationTime[instanceId] = block.timestamp;
        
        emit CounterAttestation(instanceId, value, block.timestamp);
    }
    
    // View function to verify signature chain
    function verifySignatureChain(
        string calldata instanceId,
        uint256 value,
        bytes calldata appKeySignature,
        bytes calldata kmsSignature
    ) external view returns (bool) {
        return _verifySignatureChain(instanceId, value, appKeySignature, kmsSignature);
    }
    
    // Internal function to verify signature chain
    function _verifySignatureChain(
        string memory instanceId,
        uint256 value,
        bytes memory appKeySignature,
        bytes memory kmsSignature
    ) internal view returns (bool) {
        // Verify app key signature over the counter value
        bytes32 messageHash = keccak256(abi.encodePacked(instanceId, ":", value));
        address recoveredAppKey = _recoverAddress(messageHash, appKeySignature);
        require(recoveredAppKey != address(0), "Invalid app key signature");
        
        // Verify KMS signature over the app key
        bytes32 kmsMessage = keccak256(abi.encodePacked("dstack-kms-issued:", instanceId, recoveredAppKey));
        address recoveredKMS = _recoverAddress(kmsMessage, kmsSignature);
        require(recoveredKMS == kmsRootAddress, "Invalid KMS signature");
        
        return true;
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
            r := mload(add(sig, 32))
            s := mload(add(sig, 64))
            v := byte(0, mload(add(sig, 96)))
        }
        
        return ecrecover(messageHash, v, r, s);
    }
    
    function mintNodeAccess(address to, string memory name) external onlyOwner returns (uint256) {
        require(walletToTokenId[to] == 0, "Wallet already has NFT");
        
        uint256 tokenId = _tokenIdCounter + 1;
        _tokenIdCounter = tokenId;
        
        _mint(to, tokenId);
        walletToTokenId[to] = tokenId;
        
        return tokenId;
    }
    
    function deactivateInstance(string calldata instanceId) external {
        require(instanceToToken[instanceId] != 0, "Instance not registered");
        require(walletToTokenId[msg.sender] == instanceToToken[instanceId], "Must own instance");
        
        uint256 tokenId = instanceToToken[instanceId];
        
        // Clear instance mappings
        delete instanceToToken[instanceId];
        delete tokenToInstance[tokenId];
        activeInstances[instanceId] = false;
        totalActiveNodes--;
        
        // Update required votes
        requiredVotes = totalActiveNodes > 0 ? (totalActiveNodes / 2) + 1 : 0;
        
        // Clear leader if this was the leader
        if (currentLeader == msg.sender) {
            currentLeader = address(0);
            currentLeaderTokenId = 0;
        }
        
        emit InstanceDeactivated(instanceId);
    }
    
    function electLeader() external {
        require(walletToTokenId[msg.sender] != 0, "Must own NFT");
        require(activeInstances[tokenToInstance[walletToTokenId[msg.sender]]], "Instance not active");
        
        // Simple leader election: first to call becomes leader
        if (currentLeader == address(0)) {
            currentLeader = msg.sender;
            currentLeaderTokenId = walletToTokenId[msg.sender];
            emit LeaderElected(msg.sender, currentLeaderTokenId, tokenToInstance[currentLeaderTokenId]);
        }
    }
    
    function castVote(address target, bool isNoConfidence) external {
        require(walletToTokenId[msg.sender] != 0, "Must own NFT");
        require(activeInstances[tokenToInstance[walletToTokenId[msg.sender]]], "Instance not active");
        require(target != msg.sender, "Cannot vote for yourself");
        
        // Clear previous vote if any
        address previousTarget = currentVotes[msg.sender].target;
        if (previousTarget != address(0)) {
            noConfidenceCount[previousTarget]--;
        }
        
        // Set new vote
        currentVotes[msg.sender] = Vote({
            voter: msg.sender,
            target: target,
            tokenId: walletToTokenId[msg.sender],
            isNoConfidence: isNoConfidence,
            timestamp: block.timestamp
        });
        
        if (isNoConfidence) {
            noConfidenceCount[target]++;
            
            // Check if enough votes to challenge leader
            if (target == currentLeader && noConfidenceCount[target] >= requiredVotes) {
                _challengeLeader(target);
            }
        }
        
        emit VoteCast(msg.sender, target, isNoConfidence);
    }
    
    function _challengeLeader(address oldLeader) internal {
        require(currentLeader == oldLeader, "Not current leader");
        
        // Find new leader (lowest token ID among active non-challenged nodes)
        uint256 newLeaderTokenId = type(uint256).max;
        address newLeader = address(0);
        
        for (uint256 i = 1; i <= _tokenIdCounter; i++) {
            string memory instanceId = tokenToInstance[i];
            if (activeInstances[instanceId] && noConfidenceCount[ownerOf(i)] < requiredVotes) {
                if (i < newLeaderTokenId) {
                    newLeaderTokenId = i;
                    newLeader = ownerOf(i);
                }
            }
        }
        
        if (newLeader != address(0)) {
            currentLeader = newLeader;
            currentLeaderTokenId = newLeaderTokenId;
            emit LeaderChallenged(newLeader, oldLeader, noConfidenceCount[oldLeader]);
        } else {
            // No valid leader found
            currentLeader = address(0);
            currentLeaderTokenId = 0;
        }
    }
    
    function getActiveInstances() external view returns (string[] memory) {
        string[] memory instances = new string[](totalActiveNodes);
        uint256 index = 0;
        
        for (uint256 i = 1; i <= _tokenIdCounter; i++) {
            string memory instanceId = tokenToInstance[i];
            if (activeInstances[instanceId]) {
                instances[index] = instanceId;
                instanceId;
                index++;
            }
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

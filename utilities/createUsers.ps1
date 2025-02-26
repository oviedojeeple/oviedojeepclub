# Import CSV file containing user details.
# CSV headers: email, displayName, joinDate, expirationDate
$users = Import-Csv -Path "/your/path/to/ojcMembers.csv"

# Connect to Microsoft Graph (update TenantId as needed)
Connect-MgGraph -TenantId "<TenantId>" -Scopes "User.ReadWrite.All"

# Define a default password for new users
$defaultPassword = "MyAwesomePassword1234!"

foreach ($user in $users) {
    $email = $user.email
    $displayName = $user.displayName
    $joinDate = [int]$user.joinDate         # Unix timestamp for MemberJoinedDate
    $expirationDate = [int]$user.expirationDate  # Unix timestamp for MemberExpirationDate

    # Compute normalized values for local account creation.
    # Replace "@" with "_at_"
    $normalizedEmail = $email -replace "@", "_at_"
    $mailNickname = $normalizedEmail
    $expectedUPN = "$mailNickname@oviedojeepclub.onmicrosoft.com"
    
    Write-Output "Creating user: $($displayName) with email: $($email)"
    Write-Output "Computed mailNickname: $($mailNickname), expected UPN: $($expectedUPN)"

    # Build payload for creating a local (non-federated) user.
    $createPayload = @{
        accountEnabled    = $true
        displayName       = $displayName
        userPrincipalName = $expectedUPN
        mailNickname      = $mailNickname
        passwordProfile   = @{
            forceChangePasswordNextSignIn = $true
            password                      = $defaultPassword
        }
        identities = @(
            @{
                signInType       = "emailAddress"
                issuer           = "oviedojeepclub.onmicrosoft.com"
                issuerAssignedId = $email
            }
        )
    }
    
    try {
        $createdUser = New-MgUser -BodyParameter $createPayload
        Write-Output "Created user: $($displayName)"
    }
    catch {
        Write-Output "Error creating user $($displayName) with email $($email): $($_). (User may have been created.)"
    }
    
    # Wait for the new user record to propagate.
    Start-Sleep -Seconds 30
    
    # Retrieve the created user based on expected UPN.
    try {
        $foundUser = Get-MgUser -Filter "userPrincipalName eq '$expectedUPN'" -Select "Id,UserPrincipalName" | Select-Object -First 1
    }
    catch {
        Write-Output "Error retrieving user $($displayName) by UPN: $($_)"
        continue
    }
    
    if (-not $foundUser -or -not $foundUser.Id) {
        Write-Output "User $($displayName) not found after creation."
        continue
    }
    
    $userId = $foundUser.Id

    # Build update payload to add custom extension fields and otherMails.
    $updatePayload = @{
        otherMails = @($email)
        "extension_b32ce28f40e2412fb56abae06a1ac8ab_MemberJoinedDate"     = $joinDate
        "extension_b32ce28f40e2412fb56abae06a1ac8ab_MemberExpirationDate" = $expirationDate
    }
    
    try {
        Update-MgUser -UserId $userId -BodyParameter $updatePayload
        Write-Output "Updated user $($displayName): custom extension attributes and otherMails set."
    }
    catch {
        Write-Output "Error updating user $($displayName): $($_)"
    }
}

with open('app/domains/auth/router.py', 'a') as f:
    f.write('\n@router.get("/me", response_model=CustomerOut)\nasync def get_me(current_user: Customer = Depends(get_current_user)):\n    return current_user\n')

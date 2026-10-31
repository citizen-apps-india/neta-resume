from pydantic import BaseModel


class LokSabhaMemberResponse(BaseModel):
    age: int
    categoryCode: str | None
    constName: str | None
    createdAt: str
    delhiPhone: str | None
    dob: str | None
    email: list[str | None]
    firstName: str
    freedom: str
    gender: str
    imageUrl: str | None
    initial: str | None
    lastLoksabha: int
    lastName: str | None
    lsExpr: str
    maritalStatus: str | None
    mpFirstLastName: str
    mpLastFirstName: str
    mpsno: int
    noOfTerms: int
    numberOfDaughters: int
    numberOfSons: int
    partyFname: str
    partySname: str
    permanentFaddr: str
    permanentLaddr: str
    personalPhone: str | None
    phone: str | None | list[str]
    presentFaddr: str
    presentLaddr: str
    profession: str | None
    profession2: str | None
    profileUrl: str | None
    qualification: str | None
    stateName: str | None
    status: str
    updatedAt: str


class MemberListMeta(BaseModel):
    currentPageNumber: int
    perPageSize: int
    totalElements: int
    totalPages: int


class MemberListResponse(BaseModel):
    membersDtoList: list[LokSabhaMemberResponse]
    metaDatasDto: MemberListMeta


class MemberDetailData(BaseModel):
    mpsno: int
    initial: str
    firstName: str
    lastName: str
    fullName: str
    lastFirstName: str
    constituency: str
    photoUrl: str
    stateName: str
    stateCode: str
    partyFname: str
    partySname: str
    email: str
    presentFaddr: str
    permanentLaddr: str
    personalPhone: str
    councilMinSts: str
    fatherName: str
    motherName: str
    spouseName: str
    birthPlace: str
    marriageDate: str
    sons: str
    daughters: str
    booksPublished: str
    literary: str
    social: str
    interest: str
    hobbies: str
    sports: str
    countriesVisited: str
    dateOfBirth: str
    maritalStatus: str
    qualificationName: str | None
    education: str
    facebook: str
    twitter: str
    instagram: str
    pinterest: str
    linkedIn: str
    otherInfo: str
    freedom: str
    mainProfessionName: str
    otherProfessionalName: str
    categoryCode: str
    loksabhaExpr: str
    createdAt: str
    updatedAt: str
    icNo: str | None
